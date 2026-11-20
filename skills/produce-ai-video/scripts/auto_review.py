#!/usr/bin/env python3
"""Automatic post-render review with a multimodal model.

Compresses the clip, asks one reviewer call for a JSON verdict covering
identity, space, cut continuity, artifacts and dialogue, then writes a report.

Exit codes:
  0  pass
  1  block    (stop before assembly)
  2  review   (model asked for human review, or the answer was unusable)
  3  error    (missing key/tool/input)

Configuration (environment only):
  OMNI_BASE_URL / OMNI_MODEL / OMNI_API_KEY
  falling back to DASHSCOPE_API_KEY.
"""
from __future__ import annotations

import argparse
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
QUESTION = (
    "Review this generated drama clip. Check, with timestamps: 1) identity and wardrobe "
    "continuity across cuts; 2) space and light continuity; 3) action/eyeline at each cut; "
    "4) artifacts (extra fingers, ghosting, melting textures, gibberish on-screen text); "
    "5) whether the spoken dialogue is clear and matches the visible speaker. "
    "Return JSON only: {\"status\":\"pass|review|block\",\"issues\":[{\"time\":\"00:03\","
    "\"severity\":\"block|major|minor\",\"claim\":\"...\",\"evidence\":\"...\"}]}. "
    "Use block only for a defect a viewer would immediately notice."
)


def compress(video: Path, out: Path) -> None:
    proc = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vf", "scale=384:-2",
         "-c:v", "libx264", "-crf", "30", "-preset", "veryfast",
         "-c:a", "aac", "-b:a", "48k", "-ar", "16000", "-ac", "1", str(out)],
        capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-1500:] or "ffmpeg compression failed")


def ask(video: Path, timeout: int) -> str:
    import base64
    import requests
    key = os.environ.get("OMNI_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
    if not key:
        raise RuntimeError("set OMNI_API_KEY or DASHSCOPE_API_KEY")
    data = base64.b64encode(video.read_bytes()).decode()
    response = requests.post(
        os.environ.get("OMNI_BASE_URL", DEFAULT_BASE).rstrip("/") + "/chat/completions",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        json={"model": os.environ.get("OMNI_MODEL", DEFAULT_MODEL),
              "messages": [{"role": "user", "content": [
                  {"type": "text", "text": QUESTION},
                  {"type": "video_url",
                   "video_url": {"url": "data:video/mp4;base64," + data}}]}],
              "modalities": ["text"]},
        timeout=timeout)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def parse_verdict(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        verdict = json.loads(match.group(0))
    except ValueError:
        return None
    if verdict.get("status") not in {"pass", "review", "block"}:
        return None
    return verdict


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--repair-queue", type=Path, default=None,
                        help="append block/major findings to this repair queue")
    parser.add_argument("--shot", default=None,
                        help="shot id when the video name does not contain it")
    args = parser.parse_args(argv)
    if not args.video.exists():
        print(json.dumps({"status": "error", "error": "missing video"}, ensure_ascii=False))
        return 3
    report_path = args.out or args.video.with_name(args.video.stem + "_omni_review.json")
    started = time.time()
    try:
        with tempfile.TemporaryDirectory(prefix="auto-review-") as raw:
            small = Path(raw) / "review.mp4"
            compress(args.video, small)
            text = ask(small, args.timeout)
    except Exception as exc:
        print(json.dumps({"status": "error", "error": f"{type(exc).__name__}: {exc}"[:600]},
                         ensure_ascii=False))
        return 3
    verdict = parse_verdict(text)
    if verdict is None:
        verdict = {"status": "review", "issues": [],
                   "note": "model answer was not valid JSON; read raw_text"}
        code = 2
    else:
        code = {"pass": 0, "review": 2, "block": 1}[verdict["status"]]
    report = {"video": str(args.video), "model": os.environ.get("OMNI_MODEL", DEFAULT_MODEL),
              "latency_seconds": round(time.time() - started, 1),
              "status": verdict["status"], "issues": verdict.get("issues", []),
              "verdict": verdict, "raw_text": text}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    queued = None
    if args.repair_queue is not None:
        try:
            from repair_router import append_queue, route
            tasks = route(report, video=str(args.video), shot=args.shot)
            queued = append_queue(tasks, args.repair_queue)
        except Exception as exc:  # routing must never hide the review verdict
            queued = f"error: {type(exc).__name__}: {exc}"[:300]
    print(json.dumps({"status": verdict["status"], "report": str(report_path),
                      "issues": len(verdict.get("issues", [])),
                      "repair_queued": queued}, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
