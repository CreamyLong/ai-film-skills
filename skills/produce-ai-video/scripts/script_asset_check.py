#!/usr/bin/env python3
"""Check a scene reference image against the scene contract.

The scene plan says what the space must contain (table, two chairs, old TV,
closed door). This tool sends that checklist and the reference image to a
multimodal reviewer and fails closed when a required set piece is missing or a
conflicting layout is visible.

Exit codes: 0 pass, 1 block, 2 review, 3 error.
Configuration: OMNI_BASE_URL / OMNI_MODEL / OMNI_API_KEY or DASHSCOPE_API_KEY.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import re
import sys
import time

DEFAULT_BASE = "https://cn-beijing.maas.qianwenaiapi.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3.8-omni-flash"
QUESTION = (
    "The scene contract requires these set pieces: {items}. Look at the image and "
    "return JSON only: {{\"status\":\"pass|block\",\"present\":[...],\"missing\":[...],"
    "\"conflicts\":[...]}}. A missing required piece, or a clearly different room "
    "layout (for example a bed instead of a table), is block."
)


def ask(image: Path, items: list[str], timeout: int) -> str:
    from openai import OpenAI
    key = os.environ.get("OMNI_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
    if not key:
        raise RuntimeError("set OMNI_API_KEY or DASHSCOPE_API_KEY")
    client = OpenAI(api_key=key,
                    base_url=os.environ.get("OMNI_BASE_URL", DEFAULT_BASE),
                    timeout=timeout)
    data = base64.b64encode(image.read_bytes()).decode()
    response = client.chat.completions.create(
        model=os.environ.get("OMNI_MODEL", DEFAULT_MODEL),
        messages=[{"role": "user", "content": [
            {"type": "text", "text": QUESTION.format(items=", ".join(items))},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + data}}]}],
        modalities=["text"])
    return response.choices[0].message.content


def parse(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except ValueError:
        return None
    return data if data.get("status") in {"pass", "block"} else None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--expect", required=True,
                        help="comma-separated required set pieces, e.g. 'one table,two chairs,old TV,closed door'")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args(argv)
    items = [item.strip() for item in args.expect.split(",") if item.strip()]
    if not items:
        print(json.dumps({"status": "error", "error": "empty --expect"}, ensure_ascii=False))
        return 3
    started = time.time()
    try:
        text = ask(args.image, items, args.timeout)
    except Exception as exc:
        print(json.dumps({"status": "error", "error": f"{type(exc).__name__}: {exc}"[:500]},
                         ensure_ascii=False))
        return 3
    verdict = parse(text)
    if verdict is None:
        status, code = "review", 2
        verdict = {"status": "review", "missing": [], "conflicts": [],
                   "note": "answer was not valid JSON"}
    else:
        status = verdict["status"]
        code = 0 if status == "pass" else 1
    report = {"image": str(args.image), "required": items, "status": status,
              "latency_seconds": round(time.time() - started, 1),
              "verdict": verdict, "raw_text": text}
    out = args.out or args.image.with_name(args.image.stem + "_asset_check.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": status, "report": str(out),
                      "missing": verdict.get("missing", [])}, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
