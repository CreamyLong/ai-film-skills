#!/usr/bin/env python3
"""Compare ASR output with the dialogue text declared in a scene plan.

Compare the planned line with its ASR transcript. Only a nonempty exact match
after normalisation passes. Character similarity triages mismatches for
review or blocking, even when the mismatch is a single character.

Coverage is a blocker by default: a dialogue shot with no transcript is unverified.
Exit 0 = pass, 1 = blocker, 2 = input error, 3 = review required.
"""
from __future__ import annotations

import argparse
from difflib import SequenceMatcher
import json
import re
from pathlib import Path
import sys
import unicodedata

IGNORABLE_PUNCTUATION = re.compile(
    r"""[。!?;、"“”《》()]|(?:[.,:])(?!\d)|(?<!\w)'|'(?!\w)"""
)
CJK_SPACING = re.compile(r"(?<=[\u3400-\u9fff])\s+|\s+(?=[\u3400-\u9fff])")


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower().replace("’", "'").replace("‘", "'")
    text = IGNORABLE_PUNCTUATION.sub("", text)
    return CJK_SPACING.sub("", " ".join(text.split()))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--asr", required=True, type=Path,
                        help='JSON: {"shots": {"05": "转录文本", ...}} or a flat map')
    parser.add_argument("--review", type=float, default=0.60)
    parser.add_argument("--pass-score", type=float, default=0.90,
                        help="legacy high-similarity threshold for review notes; never passes an altered line")
    parser.add_argument("--allow-missing", action="store_true",
                        help="downgrade missing transcripts from blocker to warning")
    args = parser.parse_args(argv)
    if not 0 <= args.review <= args.pass_score <= 1:
        parser.error("thresholds must satisfy 0 <= --review <= --pass-score <= 1")
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
            if not isinstance(heard, str) or not heard.strip():
                severity = "warning" if args.allow_missing else "blocker"
                if severity == "blocker":
                    blockers += 1
                results.append({"scene": scene.get("id"), "shot": sid,
                                "severity": severity, "score": None,
                                "message": "no transcript for dialogue shot"})
                continue
            a = normalise(expected)
            b = normalise(heard)
            score = SequenceMatcher(None, a, b).ratio() if a and b else 0.0
            if a and a == b:
                severity = "pass"
            elif score < args.review or not a or not b:
                severity = "blocker"
                blockers += 1
            else:
                severity = "review"
            item = {"scene": scene.get("id"), "shot": sid,
                    "severity": severity, "score": round(score, 3),
                    "expected": expected, "heard": heard}
            if severity == "review" and score >= args.pass_score:
                item["message"] = "near match changes the line; verify against the audio"
            results.append(item)
    needs_review = any(item["severity"] in {"review", "warning"} for item in results)
    status = "BLOCKED" if blockers else "REVIEW_REQUIRED" if needs_review else "PASS"
    report = {"status": status, "blockers": blockers, "results": results}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    for item in results:
        if item["severity"] in {"blocker", "review", "warning"}:
            print(f"{item['severity'].upper()} shot {item['shot']}: {item.get('score')} "
                  f"{item.get('message','')}".strip(), file=sys.stderr)
    return {"BLOCKED": 1, "REVIEW_REQUIRED": 3, "PASS": 0}[status]


if __name__ == "__main__":
    sys.exit(main())
