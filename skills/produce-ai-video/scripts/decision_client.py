#!/usr/bin/env python3
"""SystemOne decision client for repair triage.

书生-Decision-4B only judges; it never generates free text. One request carries
the finding text as ``state`` and up to 16 structured questions (noul / choice /
score). The API key is read from SYSTEMONE_API_KEY or a user-config key file kept at
mode 0600 (see KEY_FILE below); it is never logged or written anywhere else.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

DEFAULT_BASE = "https://discovery-api.intern-ai.org.cn/v1/systemone"
KEY_FILE = Path.home() / ".config" / "systemone" / "api_key"

# Defect classes must mirror repair_router.RULES so answers stay comparable.
DEFECT_CHOICES = [
    "text_prop", "prompt_contract", "speaker_split", "reference_lock",
    "environment_anchor", "artifact", "audio_gain", "assembly_truncation",
    "unknown_defect",
]
DEFECT_CRITERIA = {name: name for name in DEFECT_CHOICES}


def load_key() -> str:
    key = os.environ.get("SYSTEMONE_API_KEY")
    if key:
        return key.strip()
    if KEY_FILE.exists():
        return KEY_FILE.read_text(encoding="utf-8").strip()
    raise RuntimeError("set SYSTEMONE_API_KEY or the KEY_FILE config")


def decide(state: str, questions: dict, timeout: int = 60,
           base_url: str | None = None, model: str = "intern-decision-4b") -> dict:
    import requests
    payload = {"model": model, "state": state[:6000], "questions": questions}
    response = requests.post(base_url or os.environ.get("SYSTEMONE_BASE_URL", DEFAULT_BASE),
                             headers={"Authorization": "Bearer " + load_key(),
                                      "Content-Type": "application/json"},
                             json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    return data.get("answers", {})


TRIAGE_QUESTIONS = {
    "defect": {
        "type": "choice",
        "instructions": "This is a visual/audio defect found by a video reviewer. "
                        "Which defect class does it belong to?",
        "criteria": DEFECT_CRITERIA,
    },
    "structural": {
        "type": "noul",
        "instructions": "Can this defect be fixed by re-rendering the same shot with a new seed "
                        "or small prompt wording changes, with the same framing?",
        "criteria": {"true": "A re-render with the same structure can plausibly fix it",
                     "false": "The shot structure itself must be redesigned"},
    },
    "severity": {
        "type": "score",
        "instructions": "How much would this defect break audience immersion (0 = invisible, "
                        "4 = immediately noticeable)?",
        "criteria": ["barely visible", "minor", "noticeable", "major", "breaks immersion"],
    },
}


def triage(text: str, timeout: int = 60) -> dict:
    answers = decide(text, TRIAGE_QUESTIONS, timeout=timeout)
    result = {"defect": None, "structural": None, "severity": None}
    defect = answers.get("defect") or {}
    if defect.get("choice") in DEFECT_CHOICES:
        result["defect"] = defect["choice"]
        result["confidence"] = defect.get("confidence")
    structural = answers.get("structural") or {}
    if "noul" in structural:
        result["structural"] = structural["noul"] >= 0.5
    severity = answers.get("severity") or {}
    if "score" in severity:
        result["severity"] = round(severity["score"], 2)
    return result


CONFUSION_QUESTIONS = {
    "layer": {
        "type": "choice",
        "instructions": "A first-time viewer is confused about this while watching a drama episode. "
                        "Is the confusion mainly caused by the script or by the edit?",
        "criteria": {
            "script_gap": "the information was never written into the story",
            "edit_gap": "the script implies it but the edit/coverage fails to show it",
            "acceptable": "reasonable ambiguity a viewer can live with",
        },
    }
}


def attribute_confusion(confusion: str, timeout: int = 60) -> dict:
    answers = decide(confusion, CONFUSION_QUESTIONS, timeout=timeout)
    layer = answers.get("layer") or {}
    return {"layer": layer.get("choice"), "confidence": layer.get("confidence")}


def main(argv=None) -> int:
    ap_argv = argv if argv is not None else sys.argv[1:]
    if not ap_argv:
        print(json.dumps({"status": "ERROR", "error": "pass finding text as argument"},
                         ensure_ascii=False))
        return 3
    text = " ".join(ap_argv)
    try:
        print(json.dumps(triage(text), ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"[:400]},
                         ensure_ascii=False))
        return 3


if __name__ == "__main__":
    sys.exit(main())
