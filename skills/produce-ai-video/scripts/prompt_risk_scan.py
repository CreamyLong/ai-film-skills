#!/usr/bin/env python3
"""Prompt-level risk scan before rendering, powered by intern-decision-4b.

A prompt cannot be proven "perfect" — generation is stochastic. This tool checks
the risk classes that measurably burned renders in production:

- multi_action_with_dialogue: dialogue + several physical actions in one shot
  (EP012 shot07 burned 4 renders on this);
- text_prop_risk: a readable-text prop becomes focal (folder covers, signage);
- vague_staging: who is where / what the camera sees is under-specified.

P >= 0.7 is a block (measured threshold); 0.4-0.7 is review. The scan costs a
few hundred input tokens per shot and no GPU.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

QUESTIONS = {
    "multi_action_with_dialogue": {
        "type": "noul",
        "instructions": "This is a video-generation shot prompt that includes spoken dialogue. "
                        "Does the shot ask for more than one significant physical action "
                        "(e.g. open a drawer AND handle a folder AND walk) while the dialogue "
                        "must be lip-synced?",
        "criteria": {"true": "two or more significant actions compete with the dialogue",
                     "false": "at most one simple action accompanies the speech"},
    },
    "text_prop_risk": {
        "type": "noul",
        "instructions": "Does any prop with readable text (folder cover, document title, "
                        "letter, newspaper, signage, phone screen) become a focal or close-up "
                        "subject in this shot prompt?",
        "criteria": {"true": "a text-bearing prop is focal or in close-up",
                     "false": "no readable-text prop is emphasized"},
    },
    "vague_staging": {
        "type": "noul",
        "instructions": "A director must shoot exactly what this prompt says, with AI actors. "
                        "Are the subjects' positions or the camera framing left under-specified, "
                        "so that a reader could imagine incompatible stagings?",
        "criteria": {"true": "who stands where or what the camera sees is under-specified",
                     "false": "positions/framing are concrete and complete"},
    },
}
LABELS = {"multi_action_with_dialogue": "DIALOGUE_PLUS_ACTIONS",
          "text_prop_risk": "TEXT_PROP_CLOSEUP",
          "vague_staging": "VAGUE_STAGING"}


def scan_prompts(prompts_path: Path, shots_filter: set[str] | None) -> dict:
    data = json.loads(prompts_path.read_text(encoding="utf-8"))
    shots = data.get("shots", []) if isinstance(data, dict) else data
    if shots_filter:
        shots = [s for s in shots if str(s.get("shot")) in shots_filter]
    from decision_client import decide
    findings = []
    for shot in shots:
        prompt = shot.get("prompt", "")
        if not prompt:
            continue
        body = prompt.split("detailed_description:", 1)[-1]
        try:
            answers = decide(body[:4000], QUESTIONS, timeout=60)
        except Exception as exc:
            findings.append({"shot": shot.get("shot"), "severity": "review",
                             "code": "DECISION_API_ERROR",
                             "detail": f"{type(exc).__name__}: {exc}"[:200]})
            continue
        for key, answer in answers.items():
            p_yes = answer.get("noul", 0.0)
            if p_yes < 0.4:
                continue
            severity = "block" if p_yes >= 0.7 else "review"
            findings.append({"shot": shot.get("shot"), "severity": severity,
                             "code": LABELS[key], "risk": round(p_yes, 3)})
    blocks = [f for f in findings if f["severity"] == "block"]
    status = "block" if blocks else ("review" if findings else "pass")
    return {"status": status, "shots": len(shots), "findings": findings}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompts", required=True, type=Path)
    parser.add_argument("--shots", default="")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    wanted = {s for s in args.shots.split(",") if s} or None
    report = scan_prompts(args.prompts, wanted)
    out = args.out or args.prompts.with_name(args.prompts.stem + "_risk_scan.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "findings": len(report["findings"]),
                      "report": str(out)}, ensure_ascii=False))
    for f in report["findings"]:
        print(f"[{f['severity']}] {f['shot']} {f['code']} risk={f.get('risk')}")
    return {"pass": 0, "review": 2, "block": 1}[report["status"]]


if __name__ == "__main__":
    sys.exit(main())
