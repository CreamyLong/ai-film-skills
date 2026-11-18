#!/usr/bin/env python3
"""Check that media clips share the parameters required for a safe concat.

Reads only real stream metadata through ffprobe. It does not infer from file
names, does not modify inputs, and does not accept caller-supplied filter
graphs. Exit code 1 on any BLOCK finding, 0 otherwise.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path


def probe(path: Path) -> dict:
    if shutil.which("ffprobe") is None:
        raise SystemExit("ffprobe not found")
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"ffprobe failed for {path}: {p.stderr.strip()[:400]}")
    return json.loads(p.stdout or "{}")


def ratio(value: str | None) -> Fraction | None:
    if not value or value in ("0/0", "N/A"):
        return None
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError):
        return None


def check_one(path: Path, target: dict) -> dict:
    data = probe(path)
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    findings: list[dict] = []

    def add(severity: str, field: str, actual, expected, note: str) -> None:
        findings.append({"severity": severity, "field": field,
                         "actual": actual, "expected": expected, "note": note})

    if video is None:
        add("BLOCK", "video", None, "present", "no video stream")
    else:
        if target.get("width") and video.get("width") != target["width"]:
            add("BLOCK", "width", video.get("width"), target["width"], "resolution must match")
        if target.get("height") and video.get("height") != target["height"]:
            add("BLOCK", "height", video.get("height"), target["height"], "resolution must match")
        if target.get("pix_fmt") and video.get("pix_fmt") != target["pix_fmt"]:
            add("BLOCK", "pix_fmt", video.get("pix_fmt"), target["pix_fmt"], "pixel format must match")
        sar = video.get("sample_aspect_ratio")
        if sar and sar not in ("1:1", "0:1", "N/A") and target.get("sar", "1:1") == "1:1":
            add("BLOCK", "sample_aspect_ratio", sar, "1:1", "non-square pixels will stretch")
        fr = ratio(video.get("r_frame_rate"))
        if target.get("fps"):
            want = Fraction(str(target["fps"]))
            if fr is None or abs(float(fr) - float(want)) > 0.01:
                add("BLOCK", "r_frame_rate", str(fr), str(want), "frame rate must match")
        if str(video.get("rotation", "0")) not in ("0", "None") and int(video.get("rotation", 0)) % 360:
            add("BLOCK", "rotation", video.get("rotation"), 0, "rotation metadata must be normalized")
        cols = ("color_primaries", "color_transfer", "color_space", "color_range")
        missing = [c for c in cols if not video.get(c) or video.get(c) in ("unknown", "reserved")]
        if missing:
            add("REVIEW", "color_tags", missing, "explicit bt709/tv",
                "missing color tags make the player guess; tag them in conform")
        elif target.get("color_primaries"):
            for c, want in (("color_primaries", target.get("color_primaries", "bt709")),
                            ("color_transfer", target.get("color_transfer", "bt709")),
                            ("color_space", target.get("color_space", "bt709")),
                            ("color_range", target.get("color_range", "tv"))):
                if video.get(c) != want:
                    add("BLOCK", c, video.get(c), want, "color metadata must match")

    if audio is None:
        add("REVIEW", "audio", None, "present", "no audio stream; silent clips need an explicit track")
    else:
        if target.get("audio_rate") and int(audio.get("sample_rate", 0)) != target["audio_rate"]:
            add("BLOCK", "sample_rate", audio.get("sample_rate"), target["audio_rate"], "resample before concat")
        if target.get("audio_channels") and int(audio.get("channels", 0)) != target["audio_channels"]:
            add("BLOCK", "channels", audio.get("channels"), target["audio_channels"], "channel layout must match")
        if target.get("audio_codec") and audio.get("codec_name") != target["audio_codec"]:
            add("BLOCK", "audio_codec", audio.get("codec_name"), target["audio_codec"], "audio codec must match")

    fmt = data.get("format", {})
    dur = float(fmt.get("duration") or 0)
    if dur <= 0:
        add("BLOCK", "duration", dur, ">0", "unreadable or zero duration")

    status = "BLOCK" if any(f["severity"] == "BLOCK" for f in findings) else (
        "REVIEW" if findings else "PASS")
    return {"file": str(path), "status": status, "duration": round(dur, 3),
            "video": {k: (video or {}).get(k) for k in
                      ("codec_name", "width", "height", "pix_fmt", "r_frame_rate",
                       "sample_aspect_ratio", "color_primaries", "color_transfer",
                       "color_space", "color_range", "rotation")},
            "audio": {k: (audio or {}).get(k) for k in
                      ("codec_name", "sample_rate", "channels", "channel_layout")},
            "findings": findings}


def main() -> None:
    ap = argparse.ArgumentParser(description="Validate concat parameter consistency")
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--width", type=int, default=768)
    ap.add_argument("--height", type=int, default=1344)
    ap.add_argument("--fps", default="24/1")
    ap.add_argument("--pix-fmt", default="yuv420p")
    ap.add_argument("--audio-rate", type=int, default=48000)
    ap.add_argument("--audio-channels", type=int, default=2)
    ap.add_argument("--audio-codec", default="aac")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    target = {"width": args.width, "height": args.height, "fps": args.fps,
              "pix_fmt": args.pix_fmt, "audio_rate": args.audio_rate,
              "audio_channels": args.audio_channels, "audio_codec": args.audio_codec,
              "color_primaries": "bt709", "color_transfer": "bt709",
              "color_space": "bt709", "color_range": "tv"}
    results = [check_one(p, target) for p in args.files]
    blocked = any(r["status"] == "BLOCK" for r in results)
    if args.json:
        print(json.dumps({"target": target, "results": results,
                          "status": "BLOCK" if blocked else "PASS"}, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(f"{r['status']:6} {r['file']}  {r['duration']}s")
            for f in r["findings"]:
                print(f"       {f['severity']:6} {f['field']}: {f['actual']} -> {f['expected']} ({f['note']})")
        print("BLOCK" if blocked else "PASS")
    sys.exit(1 if blocked else 0)


if __name__ == "__main__":
    main()
