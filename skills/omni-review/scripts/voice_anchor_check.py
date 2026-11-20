#!/usr/bin/env python3
"""Blind voice-anchor verification with a multimodal model.

Audio-only judgment: the reference clip, a known-good control, and each
candidate are wrapped into black-screen mp4s so the model hears without
seeing faces (visuals bias speaker-identity judgments). Fixed protocol
question; no per-shot question generation.

Exit codes:
  0  pass     (candidates match the anchor voice)
  1  fail     (a candidate is a different speaker; re-render, do not assemble)
  2  review   (contradictory model verdicts or unusable answer)
  3  error    (missing key/tool/input)

Configuration (environment only):
  OMNI_BASE_URL / OMNI_MODEL / OMNI_API_KEY (falls back to DASHSCOPE_API_KEY)
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

DEFAULT_BASE = "https://cn-beijing.maas.qianwenaiapi.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3.8-omni-flash"

QUESTION = """All clips are AUDIO ONLY (black screen). Do not speculate about visuals.

TARGET is the reference voice of one character. GOOD is a known-good clip of the
same character from another scene (control — it should match TARGET).

For each CANDIDATE clip, judge the DOMINANT/elderly-or-expected speaker by voice
only (pitch baseline, timbre, breathiness, rasp, pacing — not words):
is the speaking voice the SAME person as TARGET? yes|no|partial + confidence
(high|medium|low) + a one-line acoustic reason.

Return JSON only:
{"control":{"same":"yes|no|partial","confidence":"...","reason":"..."},
 "candidates":[{"clip":"<label>","same":"yes|no|partial","confidence":"...","reason":"..."}],
 "summary":"..."}"""


def to_black_mp4(src: Path, out: Path) -> None:
    """Wrap audio into a tiny black-screen mp4 (audio carriers are the only
    clip type some compatible endpoints accept; measured, see
    references/voice-anchor-check.md)."""
    proc = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(src),
         "-f", "lavfi", "-i", "color=black:s=64x64:r=8",
         "-map", "0:a?", "-map", "1:v", "-c:v", "libx264", "-crf", "40",
         "-preset", "ultrafast", "-c:a", "aac", "-b:a", "64k", "-ar", "16000",
         "-ac", "1", "-shortest", str(out)],
        capture_output=True, text=True)
    if proc.returncode != 0 or not out.exists():
        raise RuntimeError(proc.stderr[-800:] or "ffmpeg wrap failed")


def ask(items: list[tuple[str, Path]], timeout: int) -> str:
    from openai import OpenAI
    key = os.environ.get("OMNI_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
    if not key:
        raise RuntimeError("set OMNI_API_KEY or DASHSCOPE_API_KEY")
    client = OpenAI(api_key=key,
                    base_url=os.environ.get("OMNI_BASE_URL", DEFAULT_BASE),
                    timeout=timeout)
    content = [{"type": "text", "text": QUESTION}]
    for label, path in items:
        data = base64.b64encode(path.read_bytes()).decode()
        content.append({"type": "text", "text": f"AUDIO {label} (black screen):"})
        content.append({"type": "video_url",
                        "video_url": {"url": "data:video/mp4;base64," + data}})
    resp = client.chat.completions.create(
        model=os.environ.get("OMNI_MODEL", DEFAULT_MODEL),
        messages=[{"role": "user", "content": content}],
        modalities=["text"])
    return resp.choices[0].message.content


def parse(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        verdict = json.loads(match.group(0))
    except ValueError:
        return None
    if not isinstance(verdict.get("candidates"), list):
        return None
    return verdict


def judge(verdict: dict) -> str:
    """Aggregate per-candidate verdicts into pass/fail/review."""
    states = []
    for cand in verdict["candidates"]:
        same = str(cand.get("same", "")).lower()
        conf = str(cand.get("confidence", "")).lower()
        if same == "no" and conf in ("high", "medium"):
            states.append("fail")
        elif same in ("yes", "partial") and conf in ("high", "medium"):
            states.append("pass")
        else:
            states.append("review")
    if "fail" in states:
        return "fail"
    if "review" in states:
        return "review"
    return "pass"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--anchor", required=True, type=Path, help="reference wav")
    ap.add_argument("--control", required=True, type=Path,
                    help="known-good clip of the same character")
    ap.add_argument("--candidates", required=True, nargs="+", type=Path)
    ap.add_argument("--label", default="", help="character name for the report")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)
    for p in [args.anchor, args.control, *args.candidates]:
        if not p.exists():
            print(json.dumps({"status": "error", "error": f"missing {p}"},
                             ensure_ascii=False))
            return 3
    report_path = args.out or args.candidates[0].with_name(
        args.candidates[0].stem + "_voice_anchor.json")
    started = time.time()
    try:
        with tempfile.TemporaryDirectory(prefix="voice-anchor-") as raw:
            tmp = Path(raw)
            items = [("TARGET_reference", args.anchor), ("GOOD_control", args.control)]
            wrapped = []
            for i, cand in enumerate(args.candidates):
                out = tmp / f"cand{i}.mp4"
                to_black_mp4(cand, out)
                wrapped.append((f"CANDIDATE_{cand.name}", out))
            for label, path in items[:]:
                out = tmp / (label + ".mp4")
                to_black_mp4(path, out)
            items = [(label, tmp / (label + ".mp4")) for label, _ in items] + wrapped
            text = ask(items, args.timeout)
    except Exception as exc:
        print(json.dumps({"status": "error",
                          "error": f"{type(exc).__name__}: {exc}"[:600]},
                         ensure_ascii=False))
        return 3
    verdict = parse(text)
    if verdict is None:
        status = "review"
        code = 2
        verdict = {"candidates": [], "note": "unusable model answer", "raw": text[:2000]}
    else:
        status = judge(verdict)
        code = {"pass": 0, "fail": 1, "review": 2}[status]
    report = {"character": args.label, "anchor": str(args.anchor),
              "control": str(args.control),
              "candidates": [str(c) for c in args.candidates],
              "model": os.environ.get("OMNI_MODEL", DEFAULT_MODEL),
              "latency_seconds": round(time.time() - started, 1),
              "status": status, "verdict": verdict}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    print(json.dumps({"status": status, "report": str(report_path)},
                     ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
