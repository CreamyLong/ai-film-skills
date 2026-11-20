#!/usr/bin/env python3
"""Cold-viewer story comprehension gate for a finished episode.

Sends the episode to the multimodal reviewer with ONE fixed, hand-authored
question set (no per-item prompt generation) and parses the structured answer.
The reviewer never sees the script; it must retell the story from picture and
sound alone and list what it cannot determine.

Exit codes: 0 pass, 1 block, 2 review, 3 error.
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

DEFAULT_BASE = "https://cn-beijing.maas.qianwenaiapi.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3.8-omni-flash"

QUESTION = (
    "你是一个第一次看这部短剧的观众，没有剧本，也不要猜测剧本。看完这一集后，只根据画面和声音，"
    "用 JSON 回答（不要输出 JSON 以外的内容）：\n"
    "{\n"
    '  "setting": "发生在哪里，几个人，各自是谁",\n'
    '  "goals": "每个人想要什么，冲突是什么",\n'
    '  "events": ["按顺序的关键事件，每个含原因和结果"],\n'
    '  "turn": "这一集最大的转折",\n'
    '  "cliffhanger": "结尾留下的悬念，没有就写 none",\n'
    '  "confusions": ["看不懂、觉得跳、动机不成立的地方，没有就空数组"],\n'
    '  "clarity": 1-10 整数,\n'
    '  "appeal": 1-10 整数\n'
    "}\n"
    "规则：clarity 衡量观众能否复述清楚；appeal 衡量想不想继续看；不确定就放进 confusions，不要编。"
)

BLOCK_CONFUSIONS = 3
REVIEW_CONFUSIONS = 1
MIN_SCORE = 6


def compress(video: Path, out: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vf", "scale=384:-2",
         "-c:v", "libx264", "-crf", "30", "-preset", "veryfast",
         "-c:a", "aac", "-b:a", "48k", "-ar", "16000", "-ac", "1", str(out)],
        check=True)


def ask(video: Path, timeout: int) -> str:
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
                  {"type": "video_url", "video_url": {"url": "data:video/mp4;base64," + data}}]}],
              "modalities": ["text"]},
        timeout=timeout)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def parse_answer(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        answer = json.loads(match.group(0))
    except ValueError:
        return None
    if not isinstance(answer, dict):
        return None
    if "setting" not in answer and "clarity" not in answer:
        return None
    return answer


def verdict(answer: dict) -> tuple[str, list[str]]:
    reasons = []
    clarity = answer.get("clarity")
    appeal = answer.get("appeal")
    if not isinstance(clarity, (int, float)) or not isinstance(appeal, (int, float)):
        reasons.append("scores missing or unusable")
    else:
        if clarity < MIN_SCORE:
            reasons.append(f"clarity {clarity} < {MIN_SCORE}")
        if appeal < MIN_SCORE:
            reasons.append(f"appeal {appeal} < {MIN_SCORE}")
    confusions = answer.get("confusions")
    count = len(confusions) if isinstance(confusions, list) else 0
    if count >= BLOCK_CONFUSIONS:
        reasons.append(f"{count} confusions >= {BLOCK_CONFUSIONS}")
    elif count >= REVIEW_CONFUSIONS:
        reasons.append(f"{count} confusions >= {REVIEW_CONFUSIONS}")
    if reasons and count >= BLOCK_CONFUSIONS:
        return "block", reasons
    return ("review" if reasons else "pass"), reasons


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args(argv)
    if not args.video.exists():
        print(json.dumps({"status": "error", "error": "missing video"}, ensure_ascii=False))
        return 3
    report_path = args.out or args.video.with_name(args.video.stem + "_story_review.json")
    try:
        with tempfile.TemporaryDirectory(prefix="story-review-") as raw:
            small = Path(raw) / "review.mp4"
            compress(args.video, small)
            text = ask(small, args.timeout)
    except Exception as exc:
        print(json.dumps({"status": "error", "error": f"{type(exc).__name__}: {exc}"[:600]},
                         ensure_ascii=False))
        return 3
    answer = parse_answer(text)
    if answer is None:
        status, reasons = "review", ["model answer was not valid JSON; read raw_text"]
    else:
        status, reasons = verdict(answer)
    report = {"video": str(args.video), "status": status, "reasons": reasons,
              "answer": answer, "raw_text": text}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": status, "report": str(report_path), "reasons": reasons},
                     ensure_ascii=False))
    return {"pass": 0, "review": 2, "block": 1}[status]


if __name__ == "__main__":
    sys.exit(main())
