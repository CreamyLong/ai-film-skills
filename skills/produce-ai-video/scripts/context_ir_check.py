#!/usr/bin/env python3
"""Check H3 Context-IR structure and label consistency. No semantic or media review."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

SECTIONS = ("subject_definitions", "summary", "retention_analysis",
            "detailed_description", "overall_soundscape", "non_diegetic_music")
VISIBLE_MARKERS = {"fully_preserved", "partially_preserved", "attribute_transfer", "weak_reference"}
AUDIO_MARKERS = {"fully_copy", "partially_copy", "reference", "weak_reference"}
TASK_TYPES = {"keyframe completion", "reference generation", "video editing",
              "video continuation", "audio reuse", "audio reference"}
LABEL = re.compile(r"<(Subject|Picture|Video|Audio) ([1-9][0-9]*)>")
SHOT = re.compile(r"\[Shot ([1-9][0-9]*)\](?: At (\d{2}):(\d{2})\.(\d{3}))?")
SPEAKER = re.compile(r"\((S[1-9][0-9]*)\)")
DIALOGUE = re.compile(r"<d>\[([^\]]+)\]\s*(.*?)</d>", re.S)
RETENTION = re.compile(r"^<(Subject|Picture|Video|Audio) ([1-9][0-9]*)>\s*(?:\(([^)]*)\))?\s*:\s*([a-z_]+)\s*-\s*(.+)$", re.M)


def split_sections(text):
    positions = []
    for name in SECTIONS:
        match = re.search(rf"^{re.escape(name)}:\s*$", text, re.M)
        if match:
            positions.append((name, match.start(), match.end()))
    sections = {}
    for index, (name, _, end) in enumerate(positions):
        stop = positions[index + 1][1] if index + 1 < len(positions) else len(text)
        sections[name] = text[end:stop].strip()
    return [name for name, _, _ in positions], sections


def audit(text, duration_seconds=None):
    findings = []

    def add(code, severity, location, advice):
        findings.append({"code": code, "severity": severity, "location": location,
                         "repair_direction": advice})

    order, sections = split_sections(text)
    if order != list(SECTIONS):
        add("SECTION_STRUCTURE", "block", "/sections",
            "Output the six sections in order: " + ", ".join(SECTIONS) + ".")
        return result(findings)

    defined = {}
    for match in re.finditer(r"^<(Subject|Picture|Video|Audio) ([1-9][0-9]*)>", sections["subject_definitions"], re.M):
        label = match.group()
        if label in defined:
            add("LABEL_DUPLICATE", "block", label, "Define each label once.")
        defined[label] = match.group(1)

    summary = sections["summary"]
    task_match = re.match(r"\[([^\]]+)\]\s", summary)
    if not task_match:
        add("TASK_TYPE_MISSING", "block", "/summary",
            "Start the summary with a bracketed task type.")
    else:
        for task in task_match.group(1).split(" + "):
            if task.strip() not in TASK_TYPES:
                add("TASK_TYPE_UNKNOWN", "review", "/summary",
                    "Use a known task type or verify the combination.")

    retained = {}
    for match in RETENTION.finditer(sections["retention_analysis"]):
        label = f"<{match.group(1)} {match.group(2)}>"
        marker = match.group(4)
        retained[label] = marker
        if label not in defined:
            add("RETENTION_UNDEFINED", "block", label,
                "Define the label in subject_definitions first.")
            continue
        allowed = AUDIO_MARKERS if match.group(1) == "Audio" else VISIBLE_MARKERS
        if marker not in allowed:
            add("RETENTION_MARKER_INVALID", "block", label,
                "Use a marker valid for this label kind.")
    for label in defined:
        if label not in retained:
            add("RETENTION_MISSING", "review", label,
                "State how this referenced content is preserved or reused.")

    body = sections["detailed_description"]
    used = {match.group() for match in LABEL.finditer(body)}
    for label in used - set(defined):
        add("BODY_LABEL_UNDEFINED", "block", label,
            "Define the label before using it in detailed_description.")
    audio_active = (body + "\n" + sections["summary"] + "\n" + sections["retention_analysis"]
                    + "\n" + sections["overall_soundscape"] + "\n" + sections["non_diegetic_music"])
    for label in set(defined) - used:
        if defined[label] == "Audio" and label in audio_active:
            continue
        add("DEFINED_LABEL_UNUSED", "review", label,
            "Use the defined label where it applies, or remove the definition.")

    shots = list(SHOT.finditer(body))
    if not shots:
        add("SHOT_MISSING", "block", "/detailed_description",
            "Mark shots with [Shot N].")
    previous = 0.0
    for index, match in enumerate(shots, 1):
        if int(match.group(1)) != index:
            add("SHOT_NUMBERING", "block", f"[Shot {match.group(1)}]",
                "Number shots sequentially from 1.")
        if index == 1:
            if match.group(2) is not None:
                add("FIRST_SHOT_TIMESTAMP", "review", "[Shot 1]",
                    "The first shot normally has no timestamp.")
            continue
        if match.group(2) is None:
            add("SHOT_CUT_TIME_MISSING", "block", f"[Shot {index}]",
                "Give the cut time as [Shot N] At MM:SS.mmm.")
            continue
        moment = int(match.group(2)) * 60 + int(match.group(3)) + int(match.group(4)) / 1000
        if moment <= previous:
            add("SHOT_CUT_TIME_ORDER", "block", f"[Shot {index}]",
                "Cut times must increase.")
        if duration_seconds is not None and moment >= duration_seconds:
            add("SHOT_CUT_TIME_RANGE", "block", f"[Shot {index}]",
                "Cut times must stay inside the total duration.")
        previous = moment

    speakers = []
    for match in SPEAKER.finditer(body):
        if match.group(1) not in speakers:
            speakers.append(match.group(1))
    for index, speaker in enumerate(speakers, 1):
        if speaker != f"S{index}":
            add("SPEAKER_NUMBERING", "block", f"({speaker})",
                "Assign speaker IDs in order of first vocal event.")

    for match in DIALOGUE.finditer(body):
        if not match.group(2).strip():
            add("DIALOGUE_EMPTY", "block", "<d>", "Dialogue tags must contain the spoken line.")
    if "<d>" in body and not DIALOGUE.search(body):
        add("DIALOGUE_FORMAT", "block", "<d>", "Write dialogue as <d>[Language] line</d>.")
    for tag in ("scenetrans", "cutoff"):
        if body.count(f"<{tag}>") % 2:
            add("CONTINUITY_TAG_UNPAIRED", "review", f"<{tag}>",
                "Cross-cut dialogue markers normally appear on both sides of the cut.")

    return result(findings)


def result(findings):
    return {"status": "BLOCK" if any(f["severity"] == "block" for f in findings) else "REVIEW_REQUIRED",
            "scope": "context_ir_structure_only", "semantic_review": "not_performed",
            "media_review": "not_performed", "findings": findings}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="prompt text file")
    parser.add_argument("--duration", type=float, default=None)
    args = parser.parse_args(argv)
    try:
        text = args.input.read_text(encoding="utf-8-sig")
    except OSError as exc:
        print(json.dumps({"status": "INVALID_INPUT", "error": str(exc)}, ensure_ascii=False))
        return 1
    report = audit(text, args.duration)
    print(json.dumps(report, ensure_ascii=False))
    return 1 if report["status"] == "BLOCK" else 2


if __name__ == "__main__":
    sys.exit(main())
