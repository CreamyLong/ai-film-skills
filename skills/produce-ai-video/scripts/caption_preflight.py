#!/usr/bin/env python3
"""Block positive H3 prompts that invite burned-in text.

Rules come from the production preflight: negative subtitle/watermark wording
in a positive prompt primes the model; technical specs and Speaker IDs are
rendered as visible text; quoted dialogue is allowed for native speech but
must be reviewed because H3 can still burn it.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

FORBIDDEN = re.compile(
    r"\b(?:subtitles?|captions?|caption\s+bar|watermarks?|burned[- ]in)\b", re.I)
SPEC = re.compile(
    r"\b(?:9\s*:\s*16|16\s*:\s*9|21\s*:\s*9|24\s*fps|30\s*fps|60\s*fps|"
    r"\d{3,4}\s*[x×]\s*\d{3,4})\b|Speaker\s*ID", re.I)
DIALOGUE_TAG = re.compile(r"<d>.*?</d>", re.S)
QUOTED_CJK = re.compile(r'"([^"\n]*[\u4e00-\u9fff][^"\n]*)"')


def check_prompt(text: str, mode: str = "native") -> list[dict]:
    findings = []

    def add(code, severity, detail):
        findings.append({"code": code, "severity": severity, "detail": detail})

    for match in FORBIDDEN.finditer(text or ""):
        add("TEXT_PRIMING", "block",
            f"positive prompt names on-screen text: {match.group(0)!r}; remove the word, not just negate it")
    for match in SPEC.finditer(text or ""):
        add("TECH_SPEC_TEXT", "block",
            f"technical spec can be burned as visible text: {match.group(0)!r}")
    if DIALOGUE_TAG.search(text or ""):
        add("DIALOGUE_TAG_REVIEW", "review",
            "<d> dialogue tags raise burned-caption risk in this runtime; prefer quoted direct speech or a silent TTS shot")
    for match in QUOTED_CJK.finditer(text or ""):
        quote = match.group(1).strip()
        if len(quote) >= 2:
            severity = "review" if mode == "native" else "block"
            add("QUOTED_DIALOGUE_TEXT", severity,
                f"quoted text may be rendered as visible text: {quote[:40]!r}")
    return findings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, help="prompt text or JSON with a 'prompt' field")
    parser.add_argument("--text", help="prompt text")
    parser.add_argument("--mode", choices=("native", "silent"), default="native",
                        help="native dialogue or silent H3 + TTS route")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.file:
        raw = args.file.read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
            text = str(data.get("prompt", raw)) if isinstance(data, dict) else raw
        except json.JSONDecodeError:
            text = raw
    elif args.text is not None:
        text = args.text
    else:
        text = sys.stdin.read()
    findings = check_prompt(text, args.mode)
    result = {"status": "BLOCK" if any(f["severity"] == "block" for f in findings)
              else ("REVIEW_REQUIRED" if findings else "PASS"),
              "mode": args.mode, "findings": findings}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for item in findings:
            print(f"{item['severity'].upper():6} {item['code']}: {item['detail']}")
        print(result["status"])
    return 1 if result["status"] == "BLOCK" else 0


if __name__ == "__main__":
    sys.exit(main())
