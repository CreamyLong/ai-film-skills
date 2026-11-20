#!/usr/bin/env python3
"""Pre-render continuity proofread across shot prompts (text-only).

For every named character the audit asks intern-decision-4b whether the staging
descriptions agree on screen side and wardrobe. It catches axis flips and
wardrobe contradictions BEFORE a render is spent. This is a judgment aid, not a
gate: findings stay `review` unless confidence is very high.

Usage:
    python3 continuity_audit.py --prompts prompts/EP012_h3_prompts_v1.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

NAME_RE = re.compile(r"\b(Shen Yuan|Shen Guodong|Han Zheng|Zhou Qiming)\b")
SIDE_RE = re.compile(
    r"(\b(?:Shen Yuan|Shen Guodong|Han Zheng|Zhou Qiming)\b[^\n.]*?"
    r"\b(left|right)\b[^\n.]*?(?:frame|side)|"
    r"\b(left|right)\b[^\n.]*?(?:frame|side)[^\n.]*?"
    r"\b(?:Shen Yuan|Shen Guodong|Han Zheng|Zhou Qiming)\b)", re.I)


def staging_sentences(prompt: str, name: str) -> list[str]:
    """Return the shot body for any shot that mentions the character."""
    body = prompt.split("detailed_description:", 1)[-1]
    block = body.split("Scene motion sequence:", 1)[0]
    if not re.search(rf"\b{re.escape(name)}\b", block):
        return []
    return [" ".join(block.split())[:900]]


def audit(prompts_path: Path, shots_filter: set[str] | None, threshold: float) -> dict:
    data = json.loads(prompts_path.read_text(encoding="utf-8"))
    shots = data.get("shots", []) if isinstance(data, dict) else data
    if shots_filter:
        shots = [s for s in shots if str(s.get("shot")) in shots_filter]

    names = set()
    for s in shots:
        for m in NAME_RE.finditer(s.get("prompt", "")):
            names.add(m.group(1))
    names = sorted(names)

    from decision_client import decide
    findings = []
    for name in names:
        evidence = {}
        for s in shots:
            sents = staging_sentences(s.get("prompt", ""), name)
            if sents:
                evidence[str(s.get("shot"))] = sents[0]
        if len(evidence) < 2:
            continue
        state = json.dumps({"character": name, "shot_staging": evidence}, ensure_ascii=False)[:5500]
        try:
            answers = decide(state, {
                "screen_side": {
                    "type": "noul",
                    "instructions": f"These staging sentences describe where {name} is placed "
                                    "across shots of the same scene. Do they place the character "
                                    "on a CONSISTENT side of the frame (or clearly describe a "
                                    "motivated camera move to the other side)?",
                    "criteria": {"true": "same side, or a stated camera-side change",
                                 "false": "contradictory sides with no motivation"},
                },
                "wardrobe": {
                    "type": "noul",
                    "instructions": f"Do all sentences describe {name}'s clothing and hair "
                                    "consistently, with no contradicting items?",
                    "criteria": {"true": "consistent or no clothing mentioned",
                                 "false": "contradicting clothing/hair items"},
                },
            }, timeout=60)
        except Exception as exc:
            findings.append({"character": name, "severity": "review",
                             "code": "DECISION_API_ERROR",
                             "detail": f"{type(exc).__name__}: {exc}"[:200]})
            continue
        for key, code, label in (("screen_side", "AXIS_CONFLICT", "screen side"),
                                 ("wardrobe", "WARDROBE_CONFLICT", "wardrobe")):
            ans = answers.get(key) or {}
            p_yes = ans.get("noul", 1.0)
            if p_yes < threshold:
                severity = "block" if p_yes < 0.35 else "review"
                findings.append({"character": name, "severity": severity, "code": code,
                                 "agreement": round(p_yes, 3),
                                 "detail": f"{label} descriptions conflict across shots",
                                 "evidence": evidence})
    blocks = [f for f in findings if f["severity"] == "block"]
    status = "block" if blocks else ("review" if findings else "pass")
    return {"status": status, "shots": len(shots), "characters": names, "findings": findings}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompts", required=True, type=Path)
    parser.add_argument("--shots", default="")
    parser.add_argument("--threshold", type=float, default=0.6)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    wanted = {s for s in args.shots.split(",") if s} or None
    report = audit(args.prompts, wanted, args.threshold)
    out = args.out or args.prompts.with_name(args.prompts.stem + "_continuity.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "findings": len(report["findings"]),
                      "report": str(out)}, ensure_ascii=False))
    for f in report["findings"]:
        print(f"[{f['severity']}] {f.get('character')} {f['code']} agree={f.get('agreement')}")
    return {"pass": 0, "review": 2, "block": 1}[report["status"]]


if __name__ == "__main__":
    sys.exit(main())
