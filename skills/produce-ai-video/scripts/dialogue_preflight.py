#!/usr/bin/env python3
"""Check H3 dialogue syntax before video generation.

This checks format only. It does not verify the words against a screenplay,
review the performance, listen to generated audio, or approve a submission.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DIALOGUE = re.compile(r"<d(?P<attrs>[^>]*)>(?P<body>.*?)</d>", re.S)
OPEN_D = re.compile(r"<d(?:\s[^>]*)?>")
CLOSE_D = re.compile(r"</d>")
SHOT = re.compile(r"\[Shot ([1-9][0-9]*)\]")
SPEAKER = re.compile(r"\((S[1-9][0-9]*)\)")
SAYS = re.compile(
    r"\b(?:says|asks|answers|replies|whispers|shouts|calls|mutters|adds|"
    r"continues|begins)\b", re.I)
VOICE = re.compile(
    r"\b(?:voice|voiced|timbre|tone|pitch|accent|whisper|breathy|raspy|"
    r"low|high|young|old|tired|guarded|calm|flat)\b|"
    r"声音|音色|嗓音|低音|中音|语速|口音|疲惫|克制|沙哑", re.I)
ELLIPSIS = re.compile(r"……|\.{3,}")
STAGE_DIRECTION = re.compile(r"[（(][^）)]{1,40}[）)]")
LANGUAGE_TAG = re.compile(r"^\[([^\]]+)\]\s*(\S.*)$", re.S)


def add(findings: list[dict], code: str, severity: str, location: str,
        advice: str, snippet: str = "") -> None:
    findings.append({
        "code": code,
        "severity": severity,
        "location": location,
        "repair_direction": advice,
        "snippet": snippet[:160],
    })


def shot_at(text: str, position: int) -> str:
    hits = list(SHOT.finditer(text, 0, position))
    return f"[Shot {hits[-1].group(1)}]" if hits else "/prompt"


def prefix_for(text: str, start: int) -> str:
    previous = text.rfind("</d>", 0, start)
    return text[previous + 4:start] if previous >= 0 else text[:start]


def audit(text: str) -> dict:
    findings: list[dict] = []
    if not text.strip():
        add(findings, "PROMPT_EMPTY", "block", "/prompt",
            "Provide the actual H3 prompt text.")
        return result(findings)

    opens = list(OPEN_D.finditer(text))
    closes = list(CLOSE_D.finditer(text))
    if len(opens) != len(closes):
        add(findings, "DIALOGUE_TAG_UNBALANCED", "block", "/prompt",
            "Pair every <d> with </d>; do not leave a partially tagged line.")
    if closes and closes[0].start() < opens[0].start():
        add(findings, "DIALOGUE_ORPHAN_CLOSE", "block", "</d>",
            "Remove the closing marker that has no opening marker.")

    if not opens:
        if re.search(r"\bsays?\b", text, re.I) or "说：" in text or "說道" in text:
            add(findings, "DIALOGUE_TAG_MISSING", "block", "/prompt",
                "A speech verb appears without a <d>[Language] line</d> block; "
                "wrap the exact spoken words or remove the speech intent.")
        return result(findings)

    speakers_seen: list[str] = []
    for index, match in enumerate(DIALOGUE.finditer(text), start=1):
        attrs = match.group("attrs").strip()
        body = match.group("body")
        location = shot_at(text, match.start())
        prefix = prefix_for(text, match.start())
        snippet = match.group(0)

        if attrs:
            add(findings, "DIALOGUE_ATTR_UNSUPPORTED", "block", location,
                "Use plain <d> with the language tag inside: "
                "<d>[中文] exact line</d>. Do not write <d zh>.",
                snippet)
            continue

        tag_match = LANGUAGE_TAG.match(body)
        if not tag_match:
            add(findings, "DIALOGUE_LANGUAGE_TAG", "block", location,
                "Start the tagged line with its language: "
                "<d>[中文] exact line</d>.", snippet)
            continue
        language, spoken = tag_match.group(1).strip(), tag_match.group(2).strip()
        if not language or not spoken:
            add(findings, "DIALOGUE_EMPTY", "block", location,
                "The language tag and the spoken line must both be non-empty.",
                snippet)
            continue
        if ELLIPSIS.search(spoken):
            add(findings, "DIALOGUE_ELLIPSIS", "block", location,
                "Remove ellipses from the spoken line. Use a period, question "
                "mark, or an action outside </d> for a pause.", snippet)
        if STAGE_DIRECTION.search(spoken):
            add(findings, "DIALOGUE_STAGE_DIRECTION", "review", location,
                "Move parenthetical performance or action notes outside </d>; "
                "H3 may read them as dialogue.", snippet)

        speaker_matches = list(SPEAKER.finditer(prefix))
        if not speaker_matches:
            add(findings, "SPEAKER_ID_MISSING", "block", location,
                "Put the speaker ID before the speech verb, e.g. "
                "Han Zheng (S1) says: <d>[中文] line</d>.", prefix[-120:])
        else:
            speaker = speaker_matches[-1].group(1)
            if speaker not in speakers_seen:
                speakers_seen.append(speaker)
            if not SAYS.search(prefix):
                add(findings, "SAYS_VERB_MISSING", "block", location,
                    "Put a speech verb before <d>: says, asks, answers, etc. "
                    "Voice and action notes belong outside the tag.")
            if not VOICE.search(prefix):
                add(findings, "VOICE_DESCRIPTION_MISSING", "review", location,
                    "For a first appearance, describe age, pitch, timbre and "
                    "pace before the speaker ID and says.")
        if not SHOT.search(text, 0, match.start()):
            add(findings, "SHOT_MISSING", "review", "/prompt",
                "Place the dialogue inside a [Shot N] section.")

    for index, speaker in enumerate(speakers_seen, start=1):
        if speaker != f"S{index}":
            add(findings, "SPEAKER_ORDER", "block", f"({speaker})",
                "Assign speaker IDs in order of first vocal event (S1, S2, ...). "
                "If IDs are fixed across the episode, renumber this prompt and "
                "record the mapping in the production ledger.")
            break

    # A prompt with multiple speakers in one shot is legal but higher risk.
    for shot_match in SHOT.finditer(text):
        start = shot_match.end()
        next_match = SHOT.search(text, start)
        end = next_match.start() if next_match else len(text)
        segment = text[start:end]
        segment_speakers = []
        for dlg in DIALOGUE.finditer(segment):
            prefix = prefix_for(segment, dlg.start())
            hits = list(SPEAKER.finditer(prefix))
            if hits:
                speaker = hits[-1].group(1)
                if speaker not in segment_speakers:
                    segment_speakers.append(speaker)
        if len(segment_speakers) > 1:
            add(findings, "MULTI_SPEAKER_SHOT", "review",
                f"[Shot {shot_match.group(1)}]",
                "Prefer one speaking character per shot. If two must speak, "
                "keep explicit (S1)/(S2) tags and verify lip-sync and speaker "
                "assignment in the generated clip.")

    return result(findings)


def result(findings: list[dict]) -> dict:
    if any(item["severity"] == "block" for item in findings):
        status = "BLOCK"
    elif findings:
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"
    return {
        "status": status,
        "scope": "h3_dialogue_format_only",
        "semantic_review": "not_performed",
        "media_review": "not_performed",
        "findings": findings,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path,
                        help="actual H3 prompt text file")
    args = parser.parse_args(argv)
    try:
        text = args.input.read_text(encoding="utf-8-sig")
    except OSError as exc:
        print(json.dumps({"status": "INVALID_INPUT", "error": str(exc)},
                         ensure_ascii=False))
        return 1
    report = audit(text)
    print(json.dumps(report, ensure_ascii=False))
    if report["status"] == "BLOCK":
        return 1
    if report["status"] == "REVIEW_REQUIRED":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
