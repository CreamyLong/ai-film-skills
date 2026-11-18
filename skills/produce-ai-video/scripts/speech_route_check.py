#!/usr/bin/env python3
"""Block silent H3 shots that visibly speak without an audio route.

Post-dubbing a speaking face is not allowed: the mouth is already performing
against generated speech. A speaking face needs either native reference audio
(H3 generates the line) or locked audio (TTS drives the mouth). Silent H3 + TTS
is only valid when the shot is a listener/reaction/back with lips closed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

VISIBLE_SPEECH = re.compile(
    r"\b(?:lips?\s+(?:moving|move)|mouth\s+(?:moving|moves)|"
    r"speaks?|speaking|says|says:)\b", re.I)
LIPS_CLOSED = re.compile(
    r"\b(?:lips?\s+(?:stay|remain|are|is)\s+closed|mouth\s+(?:stays?\s+)?closed|"
    r"lips?\s+closed)\b", re.I)


def check_speech_route(text: str, audio_refs: list[dict] | None) -> list[dict]:
    text = text or ""
    refs = audio_refs or []
    if not VISIBLE_SPEECH.search(text):
        return []
    if refs:
        modes = {str(ref.get("mode") or "reference").lower() for ref in refs}
        if "locked" in modes:
            return []
        # Reference audio lets H3 generate the speech, so the mouth matches.
        return []
    if LIPS_CLOSED.search(text):
        return []
    return [{"code": "POST_DUB_SPEAKING_FACE", "severity": "block",
             "detail": "visible speech has no audio route; use locked TTS audio, "
                       "native reference audio, or rewrite as a lips-closed listener/OS shot"}]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", required=True, help="prompt text or JSON with prompt")
    parser.add_argument("--audio-refs", default="[]",
                        help="JSON list of audio refs, or a JSON file")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    raw = args.prompt
    try:
        data = json.loads(raw)
        text = str(data.get("prompt", raw)) if isinstance(data, dict) else raw
    except json.JSONDecodeError:
        text = raw
    try:
        refs = json.loads(args.audio_refs)
    except json.JSONDecodeError:
        refs = json.loads(Path(args.audio_refs).read_text(encoding="utf-8"))
    findings = check_speech_route(text, refs)
    result = {"status": "BLOCK" if findings else "PASS", "findings": findings}
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result["status"])
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
