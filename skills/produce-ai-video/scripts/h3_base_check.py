#!/usr/bin/env python3
"""Check H3 base-mode (T2VA/I2VA/FL2VA/L2VA) prompt structure. No semantic or media review."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

MODES = ("t2va", "i2va", "fl2va", "l2va")
FIELDS = ("integrated_multimodal_description", "overall_soundscape",
          "non_diegetic_music")
REF2VA_SECTIONS = ("subject_definitions", "summary", "retention_analysis",
                   "detailed_description")
LABEL = re.compile(r"<(Picture|Video|Audio|Subject) ([1-9][0-9]*)>")
PICTURE_USE = re.compile(r"<Picture ([1-9][0-9]*)>|\bPicture ([1-9][0-9]*)\b")
SHOT = re.compile(r"\[Shot ([1-9][0-9]*)\](?: At (\d{2}):(\d{2})\.(\d{3}))?")
SPEAKER_GROUP = re.compile(r"\((S[1-9][0-9]*(?:,S[1-9][0-9]*)*)\)")
DIALOGUE = re.compile(r"<d>\[([^\]]+)\]\s*(.*?)</d>", re.S)
I2VA_INSTRUCTION = re.compile(
    r"^For the target video, at 0\.00 seconds into the target video, "
    r"<Picture 1> \(from \[Shot 1\]\) is fully referenced\.?\s*$")
FL2VA_INSTRUCTION = re.compile(
    r"^How the reference pictures align with the target video\s*—\s*"
    r"<?Picture 1>? \(from \[?Shot 1\]?\) aligns with the 0\.00-second mark "
    r"of the target video;\s*<?Picture 2>? \(from \[?Shot ([1-9][0-9]*)\]?\) "
    r"aligns with the (\d+)\.(\d{2})-second mark of the target video\.?\s*$")
L2VA_INSTRUCTION = re.compile(
    r"^How the reference pictures align with the target video\s*—\s*"
    r"<Picture 1> \(from \[Shot ([1-9][0-9]*)\]\) aligns with the "
    r"(\d+)\.(\d{2})-second mark of the target video\.?\s*$")
EXPECTED_PICTURES = {"t2va": set(), "i2va": {1}, "fl2va": {1, 2}, "l2va": {1}}


def split_fields(text):
    positions = []
    for name in FIELDS:
        match = re.search(rf"^{re.escape(name)}:", text, re.M)
        if match:
            positions.append((name, match.start(), match.end()))
    fields = {}
    for index, (name, _, end) in enumerate(positions):
        stop = positions[index + 1][1] if index + 1 < len(positions) else len(text)
        fields[name] = text[end:stop].strip()
    return [name for name, _, _ in positions], fields


def audit(text, mode, duration_seconds=None):
    findings = []

    def add(code, severity, location, advice):
        findings.append({"code": code, "severity": severity, "location": location,
                         "repair_direction": advice})

    if mode not in MODES:
        add("MODE_UNKNOWN", "block", "/mode",
            "Declare the H3 base mode: " + ", ".join(MODES) + ".")
        return result(findings)

    for name in REF2VA_SECTIONS:
        if re.search(rf"^{re.escape(name)}:\s*$", text, re.M):
            add("SECTION_MIXED_FORMAT", "block", name,
                "Full-reference sections do not belong in a base-mode prompt; "
                "compile the whole prompt in one shell.")
    first_line = text.strip().split("\n", 1)[0].strip() if text.strip() else ""

    if mode == "t2va":
        if not first_line.startswith(FIELDS[0] + ":"):
            add("INSTRUCTION_UNEXPECTED", "block", "/prompt",
                "T2VA has no image-alignment instruction; start directly with "
                "integrated_multimodal_description.")
    else:
        instruction = {"i2va": I2VA_INSTRUCTION, "fl2va": FL2VA_INSTRUCTION,
                       "l2va": L2VA_INSTRUCTION}[mode]
        match = instruction.match(first_line)
        if not match:
            add("INSTRUCTION_MISSING", "block", "/prompt",
                f"The first line of a {mode.upper()} prompt must be its "
                "documented alignment instruction.")
        else:
            head, _, tail = text.partition("\n")
            if tail[:1] != "\n":
                add("INSTRUCTION_SPACING", "review", "/prompt",
                    "Leave one blank line between the instruction and the "
                    "core fields.")
            if match.groups():
                last_shot = int(match.group(1))
                mark = int(match.group(2)) + int(match.group(3)) / 100
                shots_in_body = [int(m.group(1)) for m in SHOT.finditer(text)]
                if shots_in_body and last_shot != max(shots_in_body):
                    add("INSTRUCTION_SHOT_MISMATCH", "block", "/prompt",
                        "The instruction's shot index must be the final shot.")
                if duration_seconds is not None and abs(mark - duration_seconds) > 0.05:
                    add("INSTRUCTION_TIME_MISMATCH", "block", "/prompt",
                        "The alignment time must equal the effective video "
                        "duration to two decimals.")

    order, fields = split_fields(text)
    if order != list(FIELDS):
        add("FIELD_STRUCTURE", "block", "/fields",
            "Output the three fields in order: " + ", ".join(FIELDS) + ".")
        return result(findings)

    body = fields["integrated_multimodal_description"]
    label_hits = list(LABEL.finditer(text))
    pictures = {int(m.group(1) or m.group(2)) for m in PICTURE_USE.finditer(text)}
    for match in label_hits:
        if match.group(1) != "Picture":
            add("LABEL_FORBIDDEN", "block", match.group(),
                "Subject/Video/Audio labels belong to the full-reference "
                "format; base mode only uses <Picture N>.")
    unexpected = pictures - EXPECTED_PICTURES[mode]
    if unexpected:
        add("PICTURE_LABEL_UNEXPECTED", "block",
            "<Picture %d>" % sorted(unexpected)[0],
            f"{mode.upper()} uses pictures {sorted(EXPECTED_PICTURES[mode]) or 'none'}; "
            "remove or renumber the rest.")
    body_pictures = {int(m.group(1) or m.group(2))
                     for m in PICTURE_USE.finditer(body)}
    missing = EXPECTED_PICTURES[mode] - body_pictures
    if missing:
        add("PICTURE_LABEL_MISSING", "review",
            "<Picture %d>" % sorted(missing)[0],
            "Reference the keyframe picture where it actually anchors.")

    shots = list(SHOT.finditer(body))
    if not shots:
        add("SHOT_MISSING", "block", "/integrated_multimodal_description",
            "Mark shots with [Shot N].")
    previous = 0.0
    for index, match in enumerate(shots, 1):
        if int(match.group(1)) != index:
            add("SHOT_NUMBERING", "block", f"[Shot {match.group(1)}]",
                "Number shots sequentially from 1.")
        if index == 1:
            if match.group(2) is not None:
                add("FIRST_SHOT_TIMESTAMP", "review", "[Shot 1]",
                    "The first shot has no timestamp.")
            continue
        if match.group(2) is None:
            add("SHOT_CUT_TIME_MISSING", "block", f"[Shot {index}]",
                "Give the cut time as [Shot N] At MM:SS.mmm.")
            continue
        moment = (int(match.group(2)) * 60 + int(match.group(3))
                  + int(match.group(4)) / 1000)
        if moment <= previous:
            add("SHOT_CUT_TIME_ORDER", "block", f"[Shot {index}]",
                "Cut times must increase.")
        if duration_seconds is not None and moment >= duration_seconds:
            add("SHOT_CUT_TIME_RANGE", "block", f"[Shot {index}]",
                "Cut times must stay inside the total duration.")
        previous = moment

    speakers = []
    for match in SPEAKER_GROUP.finditer(body):
        for speaker in match.group(1).split(","):
            if speaker not in speakers:
                speakers.append(speaker)
    for index, speaker in enumerate(speakers, 1):
        if speaker != f"S{index}":
            add("SPEAKER_NUMBERING", "block", f"({speaker})",
                "Assign speaker IDs in order of first vocal event.")

    for match in DIALOGUE.finditer(body):
        if not match.group(2).strip():
            add("DIALOGUE_EMPTY", "block", "<d>",
                "Dialogue tags must contain the spoken line.")
    if "<d>" in body and not DIALOGUE.search(body):
        add("DIALOGUE_FORMAT", "block", "<d>",
            "Write dialogue as <d>[Language] line</d>.")
    for tag in ("scenetrans", "cutoff"):
        if body.count(f"<{tag}>") % 2:
            add("CONTINUITY_TAG_UNPAIRED", "review", f"<{tag}>",
                "Cross-cut dialogue markers normally appear on both sides "
                "of the cut.")

    return result(findings)


def result(findings):
    return {"status": "BLOCK" if any(f["severity"] == "block" for f in findings) else "REVIEW_REQUIRED",
            "scope": "h3_base_structure_only", "semantic_review": "not_performed",
            "media_review": "not_performed", "findings": findings}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="prompt text file")
    parser.add_argument("--mode", required=True, choices=MODES)
    parser.add_argument("--duration", type=float, default=None)
    args = parser.parse_args(argv)
    try:
        text = args.input.read_text(encoding="utf-8-sig")
    except OSError as exc:
        print(json.dumps({"status": "INVALID_INPUT", "error": str(exc)}, ensure_ascii=False))
        return 1
    report = audit(text, args.mode, args.duration)
    print(json.dumps(report, ensure_ascii=False))
    return 1 if report["status"] == "BLOCK" else 2


if __name__ == "__main__":
    sys.exit(main())
