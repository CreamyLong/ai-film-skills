#!/usr/bin/env python3
"""Mechanical QC of generated media via ffprobe/ffmpeg. No model, no semantic review.

Checks what signal inspection can prove: container/codec readability, stream
presence, duration/resolution/frame-rate against the declared expectation,
black and frozen frame intervals, audio level and integrated loudness, and
subtitle coverage against declared dialogue. It can also emit a contact-sheet
image as review evidence. Passing never proves the clip is semantically or
visually acceptable.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

DURATION_TOLERANCE_S = 0.25
FPS_TOLERANCE = 0.6
BLACK_FRACTION_BLOCK = 0.15
FREEZE_FRACTION_REVIEW = 0.30
SILENCE_MEAN_DB = -60.0
DEFAULT_LUFS_RANGE = (-27.0, -9.0)
SUBTITLE_TIME_TOLERANCE_S = 0.5

FFPROBE_FORMAT = ["ffprobe", "-v", "error", "-show_format",
                  "-show_streams", "-of", "json"]
BLACKDETECT = ["ffmpeg", "-hide_banner", "-nostats", "-i",
               "{in}", "-vf", "blackdetect=d=0.1:pic_th=0.98", "-an", "-f", "null", "-"]
FREEZEDETECT = ["ffmpeg", "-hide_banner", "-nostats", "-i",
                "{in}", "-vf", "freezedetect=n=0.001:d=0.5", "-an", "-f", "null", "-"]
VOLUME = ["ffmpeg", "-hide_banner", "-nostats", "-i", "{in}",
          "-af", "volumedetect", "-vn", "-f", "null", "-"]
EBUR128 = ["ffmpeg", "-hide_banner", "-nostats", "-i", "{in}",
           "-af", "ebur128=peak=true", "-vn", "-f", "null", "-"]
CONTACT_SHEET = ["ffmpeg", "-y", "-v", "error", "-i", "{in}",
                 "-vf", "fps=1/2,scale=320:-1,tile=4x4", "-frames:v", "1", "{out}"]

_BLACK_RE = re.compile(r"black_start:(\d+(?:\.\d+)?)\s+black_end:(\d+(?:\.\d+)?)")
_FREEZE_START_RE = re.compile(r"freeze_start: (\d+(?:\.\d+)?)")
_FREEZE_END_RE = re.compile(r"freeze_end: (\d+(?:\.\d+)?)")
_MEAN_VOL_RE = re.compile(r"mean_volume: (-?\d+(?:\.\d+)?) dB")
_MAX_VOL_RE = re.compile(r"max_volume: (-?\d+(?:\.\d+)?) dB")
_LUFS_RE = re.compile(r"I: +(-?\d+(?:\.\d+)?) LUFS")


def _run(command, timeout=120):
    proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr


def probe(path, runner=_run):
    code, out, _ = runner(FFPROBE_FORMAT + [str(path)])
    if code != 0:
        return None
    try:
        return json.loads(out)
    except ValueError:
        return None


def video_stream(data):
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            return stream
    return None


def audio_stream(data):
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "audio":
            return stream
    return None


def stream_duration(stream, data):
    for candidate in (stream.get("duration"), (data.get("format") or {}).get("duration")):
        try:
            return float(candidate)
        except (TypeError, ValueError):
            continue
    return None


def stream_fps(stream):
    raw = stream.get("avg_frame_rate") or stream.get("r_frame_rate") or ""
    try:
        num, _, den = raw.partition("/")
        return float(num) / float(den or 1)
    except (ValueError, ZeroDivisionError):
        return None


def parse_intervals(stderr, start_re, end_re=None):
    if end_re is None:
        return [(float(a), float(b)) for a, b in start_re.findall(stderr)]
    starts = [float(x) for x in start_re.findall(stderr)]
    ends = [float(x) for x in end_re.findall(stderr)]
    return list(zip(starts, ends))


def parse_srt(text):
    cues = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [x.strip() for x in block.strip().splitlines() if x.strip()]
        timing = next((x for x in lines if "-->" in x), None)
        if not timing:
            continue
        start_s, _, end_s = timing.partition("-->")
        try:
            start = _srt_seconds(start_s.strip())
            end = _srt_seconds(end_s.strip().split()[0])
        except ValueError:
            continue
        body = " ".join(x for x in lines if x != timing and not x.isdigit())
        cues.append({"start": start, "end": end, "text": body})
    return cues


def _srt_seconds(value):
    main, _, millis = value.partition(",")
    hours, minutes, seconds = main.split(":")
    return (int(hours) * 3600 + int(minutes) * 60 + int(seconds)
            + int(millis or 0) / 1000)


def audit(path, expect_duration=None, expect_size=None, expect_fps=None,
          expect_dialogue=False, srt_text=None, dialogue=None,
          loudness_range=DEFAULT_LUFS_RANGE, contact_sheet=None,
          runner=_run):
    """Return the QC report. ``runner`` is injectable for tests."""
    findings = []

    def add(code, severity, location, advice):
        findings.append({"code": code, "severity": severity,
                         "location": location, "repair_direction": advice})

    if runner is _run and shutil.which("ffprobe") is None:
        return {"status": "INVALID_INPUT", "error": "ffprobe unavailable",
                "scope": "media_mechanical_qc_only", "findings": []}
    if not os.path.isfile(path):
        return {"status": "INVALID_INPUT", "error": "media file unreadable",
                "scope": "media_mechanical_qc_only", "findings": []}

    data = probe(path, runner)
    if data is None:
        add("CONTAINER_UNREADABLE", "block", str(path),
            "Repair or regenerate; the file cannot be probed.")
        return report(findings, {})

    measurements = {}
    vs = video_stream(data)
    if vs is None:
        add("VIDEO_STREAM_MISSING", "block", str(path),
            "The file has no video stream.")
    else:
        width, height = vs.get("width"), vs.get("height")
        fps = stream_fps(vs)
        measurements.update({"width": width, "height": height, "fps": fps})
        if expect_size and (width, height) != tuple(expect_size):
            add("RESOLUTION_MISMATCH", "block", f"{width}x{height}",
                "Deliver the declared frame size or correct the declaration.")
        if expect_fps and fps and abs(fps - expect_fps) > FPS_TOLERANCE:
            add("FPS_MISMATCH", "review", f"{fps:.2f}",
                "Confirm the intended frame rate before assembly.")

    duration = stream_duration(vs or {}, data)
    measurements["duration_seconds"] = duration
    if expect_duration is not None and duration is not None:
        if abs(duration - expect_duration) > DURATION_TOLERANCE_S:
            add("DURATION_MISMATCH", "block",
                f"{duration:.2f}s vs {expect_duration:.2f}s",
                "Regenerate to the declared duration or fix the plan/ledger.")

    audio = audio_stream(data)
    measurements["has_audio"] = audio is not None
    if audio is None:
        add("AUDIO_STREAM_MISSING",
            "block" if expect_dialogue else "review", str(path),
            "This shot expects audible content; verify the audio route.")

    if vs is not None:
        code, _, stderr = runner([x.format(**{"in": path, "out": ""})
                                  for x in BLACKDETECT])
        black = parse_intervals(stderr, _BLACK_RE) if code == 0 else []
        measurements["black_intervals"] = black
        black_total = sum(b - a for a, b in black)
        if duration and black_total / duration > BLACK_FRACTION_BLOCK:
            add("BLACK_FRAMES", "block", f"{black_total:.2f}s black",
                "The clip is mostly black; regenerate or fix the route.")
        elif black:
            add("BLACK_FRAMES", "review", str(black[:3]),
                "Confirm these black intervals are intentional.")

        code, _, stderr = runner([x.format(**{"in": path, "out": ""})
                                  for x in FREEZEDETECT])
        frozen = parse_intervals(stderr, _FREEZE_START_RE, _FREEZE_END_RE) \
            if code == 0 else []
        measurements["frozen_intervals"] = frozen
        frozen_total = sum(b - a for a, b in frozen)
        if duration and frozen_total / duration > FREEZE_FRACTION_REVIEW:
            add("FROZEN_FRAMES", "review", f"{frozen_total:.2f}s frozen",
                "Long frozen spans look like a still image; verify actual motion.")

    if audio is not None:
        code, _, stderr = runner([x.format(**{"in": path, "out": ""})
                                  for x in VOLUME])
        mean = _MEAN_VOL_RE.search(stderr)
        maxv = _MAX_VOL_RE.search(stderr)
        if mean:
            measurements["mean_volume_db"] = float(mean.group(1))
            if expect_dialogue and float(mean.group(1)) < SILENCE_MEAN_DB:
                add("AUDIO_SILENT", "block", f"{mean.group(1)} dB",
                    "The track is effectively silent while dialogue is expected.")
        if maxv:
            measurements["max_volume_db"] = float(maxv.group(1))
        code, _, stderr = runner([x.format(**{"in": path, "out": ""})
                                  for x in EBUR128])
        lufs = _LUFS_RE.findall(stderr)
        if lufs:
            integrated = float(lufs[-1])
            measurements["integrated_lufs"] = integrated
            low, high = loudness_range
            if integrated < low or integrated > high:
                add("LOUDNESS_OUT_OF_RANGE", "review", f"{integrated:.1f} LUFS",
                    "Verify the loudness target for the delivery route.")

    if srt_text is not None:
        cues = parse_srt(srt_text)
        measurements["subtitle_cues"] = len(cues)
        for cue in cues:
            if expect_duration is not None and \
                    cue["end"] > expect_duration + SUBTITLE_TIME_TOLERANCE_S:
                add("SUBTITLE_OUT_OF_RANGE", "block",
                    f"{cue['start']:.2f}-{cue['end']:.2f}s",
                    "Subtitle cues must stay inside the clip duration.")
        joined = " ".join(c["text"] for c in cues)
        if not joined.strip():
            add("SUBTITLE_EMPTY", "block", str(path),
                "The subtitle file has no usable cues.")
        for line in (dialogue or []):
            text = (line.get("text") or "").strip()
            if text and text not in joined:
                add("SUBTITLE_DIALOGUE_MISSING", "block", text[:30],
                    "Every planned spoken line needs a matching subtitle cue.")

    artifacts = {}
    if contact_sheet:
        out_path = str(contact_sheet)
        code, _, stderr = runner(
            [x.format(**{"in": path, "out": out_path}) for x in CONTACT_SHEET])
        if code == 0 and os.path.exists(out_path):
            artifacts["contact_sheet"] = out_path
        else:
            add("CONTACT_SHEET_FAILED", "review", out_path,
                "Generate the review sheet another way; it is evidence, not approval.")

    return report(findings, measurements, artifacts)


def report(findings, measurements, artifacts=None):
    return {"status": "BLOCK" if any(f["severity"] == "block" for f in findings)
            else "REVIEW_REQUIRED",
            "scope": "media_mechanical_qc_only",
            "semantic_review": "not_performed",
            "visual_review": "not_performed",
            "measurements": measurements,
            "artifacts": artifacts or {},
            "findings": findings}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--expect-duration", type=float, default=None)
    parser.add_argument("--expect-size", default=None, help="WxH, e.g. 1280x720")
    parser.add_argument("--expect-fps", type=float, default=None)
    parser.add_argument("--expect-dialogue", action="store_true")
    parser.add_argument("--srt", type=Path, default=None)
    parser.add_argument("--dialogue", type=Path, default=None,
                        help="JSON list of {\"text\": ...} expected lines")
    parser.add_argument("--loudness", default=None, help="min,max LUFS range")
    parser.add_argument("--contact-sheet", type=Path, default=None)
    args = parser.parse_args(argv)

    size = None
    if args.expect_size:
        try:
            w, h = args.expect_size.lower().split("x")
            size = (int(w), int(h))
        except ValueError:
            print(json.dumps({"status": "INVALID_INPUT",
                              "error": "--expect-size must be WxH"}))
            return 1
    loudness = DEFAULT_LUFS_RANGE
    if args.loudness:
        try:
            low, high = args.loudness.split(",")
            loudness = (float(low), float(high))
        except ValueError:
            print(json.dumps({"status": "INVALID_INPUT",
                              "error": "--loudness must be min,max"}))
            return 1
    srt_text = dialogue = None
    try:
        if args.srt:
            srt_text = args.srt.read_text(encoding="utf-8-sig")
        if args.dialogue:
            dialogue = json.loads(args.dialogue.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "INVALID_INPUT", "error": str(exc)},
                         ensure_ascii=False))
        return 1

    result = audit(str(args.input), expect_duration=args.expect_duration,
                   expect_size=size, expect_fps=args.expect_fps,
                   expect_dialogue=args.expect_dialogue, srt_text=srt_text,
                   dialogue=dialogue, loudness_range=loudness,
                   contact_sheet=args.contact_sheet)
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result["status"] in ("BLOCK", "INVALID_INPUT") else 2


if __name__ == "__main__":
    sys.exit(main())
