#!/usr/bin/env python3
"""Compare ASR output with the dialogue text declared in a scene plan.

This is the missing gate for "the prompt said one line, the model spoke
another". It takes a plan plus a JSON map of shot id -> transcript, normalises
punctuation and whitespace, and scores character similarity.

  <0.60  blocker   the spoken content is effectively a different line
  0.60-0.90 review  recognisable but altered
  >=0.90  pass

Coverage is a blocker by default: a dialogue shot with no transcript is unverified.
Exit 0 = no blocker, 1 = blocker, 2 = input error.
"""
from __future__ import annotations

import argparse
from difflib import SequenceMatcher
import json
import re
from pathlib import Path
import sys

CJK = re.compile(r"[\u4e00-\u9fff]")


def normalise(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[，。！？、；：,.!?;:\"'“”‘’（）()《》\u3000]", "", text)
    return text


def similarity(expected: str, heard: str) -> float:
    a, b = normalise(expected), normalise(heard)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--asr", required=True, type=Path,
                        help='JSON: {"shots": {"05": "转录文本", ...}} or a flat map')
    parser.add_argument("--review", type=float, default=0.60)
    parser.add_argument("--pass-score", type=float, default=0.90)
    parser.add_argument("--allow-missing", action="store_true",
                        help="downgrade missing transcripts from blocker to warning")
    args = parser.parse_args(argv)
    try:
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        raw = json.loads(args.asr.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2
    transcripts = raw.get("shots", raw) if isinstance(raw, dict) else {}

    results, blockers = [], 0
    for scene in plan.get("scenes", []):
        for shot in scene.get("shots", []):
            speaker = shot.get("speaker")
            expected = (shot.get("line") or "").strip()
            if not speaker or not expected:
                continue
            sid = str(shot.get("id"))
            heard = transcripts.get(sid)
            if not heard:
                severity = "warning" if args.allow_missing else "blocker"
                if severity == "blocker":
                    blockers += 1
                results.append({"scene": scene.get("id"), "shot": sid,
                                "severity": severity, "score": None,
                                "message": "no transcript for dialogue shot"})
                continue
            score = similarity(expected, heard)
            if score < args.review:
                severity = "blocker"
                blockers += 1
            elif score < args.pass_score:
                severity = "review"
            else:
                severity = "pass"
            results.append({"scene": scene.get("id"), "shot": sid,
                            "severity": severity, "score": round(score, 3),
                            "expected": expected, "heard": heard})
    report = {"status": "BLOCKED" if blockers else "PASS",
              "blockers": blockers, "results": results}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    for item in results:
        if item["severity"] in {"blocker", "review"}:
            print(f"{item['severity'].upper()} shot {item['shot']}: {item.get('score')} "
                  f"{item.get('message','')}".strip(), file=sys.stderr)
    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
