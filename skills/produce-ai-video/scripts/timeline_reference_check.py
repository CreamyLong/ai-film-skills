#!/usr/bin/env python3
"""Check that every TimelineDirector segment gets the references it names.

The planner keeps a global image list; each segment carries its own
``images`` ids. A segment prompt can mention <Subject N> or a room while the
segment's image list omits the matching picture. When that happens the model
invents wardrobe, space or people. This checker fails closed on those cases.

Input: a JSON file containing ``timeline_data`` (string or object), or the
timeline object itself. Also accepts a ComfyUI API graph with a
MiniMaxH3TimelinePlanner node.

Exit codes: 0 pass, 1 block, 2 review, 3 error.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

SUBJECT_USE = re.compile(r"<Subject (\d+)>")
SUBJECT_DEF = re.compile(r"<Picture (\d+)> is <Subject (\d+)>")
DEF_LINE = re.compile(r"<Picture (\d+)>[^" + "\n" + r"]*")
FACE_WORDS = re.compile(r"face|portrait|hero|'s face", re.I)
SCENE_WORDS = re.compile(r"interior|room|scene|street|office|environment|safehouse", re.I)
AUDIO_DEF = re.compile(r"<Audio (\d+)> is the voice-timbre reference for <Subject (\d+)>")
DIALOGUE = re.compile(r"<Subject (\d+)>[^\n<]*?says,\s*<d>")
VIDEO_DEF = re.compile(r"<Video (\d+)>")
SPACE = re.compile(r"\b(?:room|door|table|wall|interior|exterior|street|office|apartment|warehouse|corridor)\b", re.I)
SCENE_NAME = re.compile(r"(?:^|/)(s\d+_|scene|room|interior|exterior)", re.I)
KNOWN_CHARACTERS = {
    "shen yuan": re.compile(r"\bShen Yuan\b|沈远", re.I),
    "shen guodong": re.compile(r"\bShen Guodong\b|沈国栋", re.I),
    "han zheng": re.compile(r"\bHan ?Zheng\b|韩[正峥]", re.I),
    "zhou qiming": re.compile(r"\bZhou ?Qiming\b|周启明", re.I),
}


def load_timeline(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "timeline_data" not in data:
        # ComfyUI API graph: find the planner node's timeline_data input.
        for node in data.values():
            if isinstance(node, dict) and node.get("class_type") == "MiniMaxH3TimelinePlanner":
                data = (node.get("inputs") or {}).get("timeline_data")
                break
    if isinstance(data, dict) and "timeline_data" in data:
        data = data["timeline_data"]
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, dict):
        raise ValueError("timeline_data is not an object")
    return data


def check(timeline: dict) -> list[dict]:
    images = timeline.get("images") or []
    audios = timeline.get("audios") or []
    clips = timeline.get("videoClips") or []
    by_id = {img.get("id"): img for img in images}
    order = [img.get("id") for img in images]
    audio_order = [a.get("id") for a in audios]
    findings = []

    segments = ((timeline.get("segmentConfig") or {}).get("segments") or [])
    previous = None
    for index, seg in enumerate(segments, 1):
        prompt = seg.get("prompt", "") or ""
        attached = list(seg.get("images") or [])
        attached_audio = list(seg.get("audios") or [])
        label = f"segment {index}"

        def add(severity: str, code: str, detail: str, fix: str) -> None:
            findings.append({"segment": index, "severity": severity, "code": code,
                             "detail": detail, "fix": fix})

        defs = {int(subject): int(picture) for picture, subject in SUBJECT_DEF.findall(prompt)}
        used = {int(s) for s in SUBJECT_USE.findall(prompt)}
        for subject in sorted(used):
            picture = defs.get(subject)
            if picture is None:
                add("review", "SUBJECT_WITHOUT_PICTURE",
                    f"{label}: <Subject {subject}> is used but not defined by a <Picture N>",
                    "Add the subject definition or remove the reference.")
                continue
            # Per-segment numbering: <Picture N> is the Nth image of THIS
            # segment's own images list, not the global gallery order.
            if picture > len(attached):
                add("block", "PICTURE_OUT_OF_RANGE",
                    f"{label}: <Picture {picture}> exceeds this segment's images ({len(attached)})",
                    "Fix the picture numbering.")
                continue
            image_id = attached[picture - 1]
            def_line = next((m.group(0) for m in DEF_LINE.finditer(prompt)
                             if int(m.group(1)) == picture), "")
            filename = str(by_id.get(image_id, {}).get("file", "")) + "/" + str(by_id.get(image_id, {}).get("name", ""))
            is_scene_file = bool(SCENE_NAME.search(filename))
            if FACE_WORDS.search(def_line) and is_scene_file:
                add("block", "REF_ROLE_MISMATCH",
                    f"{label}: <Picture {picture}> is declared as a face/portrait but the attached image "
                    f"is a scene ({filename})",
                    "Fix the per-segment picture numbering so the face picture is <Picture 1> of this segment.")
            if SCENE_WORDS.search(def_line) and not is_scene_file:
                add("block", "REF_ROLE_MISMATCH",
                    f"{label}: <Picture {picture}> is declared as the scene but the attached image is not "
                    f"({filename})",
                    "Fix the per-segment picture numbering so the scene picture is the declared index.")

        if SPACE.search(prompt):
            scene_ids = [i for i in attached
                         if SCENE_NAME.search(str(by_id.get(i, {}).get("file", ""))
                                              + "/" + str(by_id.get(i, {}).get("name", "")))]
            if not scene_ids:
                add("block", "MISSING_SCENE_REF",
                    f"{label}: the prompt names a space but no scene image is attached ({attached})",
                    "Attach the scene image to this segment; otherwise the model invents a room.")

        if len(images) > 4 and len(attached) == len(images):
            add("review", "ALL_REFS_ATTACHED",
                f"{label}: every global reference is attached ({len(attached)}); salient images can steal identity",
                "Attach only the subjects and scene this segment needs.")

        audio_defs = {int(subject): int(audio) for audio, subject in AUDIO_DEF.findall(prompt)}
        speakers = {int(s) for s in DIALOGUE.findall(prompt)}
        for subject in sorted(speakers):
            audio = audio_defs.get(subject)
            if audio is None:
                add("block", "MISSING_VOICE_ANCHOR",
                    f"{label}: <Subject {subject}> speaks but has no <Audio N> timbre definition",
                    "Add the voice-timbre reference for this speaker; silent H3 cannot dub "
                    "a lips-visible speaker.")
                continue
            if audio > len(attached_audio):
                add("block", "AUDIO_OUT_OF_RANGE",
                    f"{label}: <Audio {audio}> exceeds this segment's audios ({len(attached_audio)})",
                    "Fix the audio numbering.")
                continue
            audio_id = attached_audio[audio - 1]
        named = [name for name, pat in KNOWN_CHARACTERS.items() if pat.search(prompt)]
        defined = set()
        for m in re.finditer(r"<Subject \d+>[^\n:]*?,\s*([A-Za-z][A-Za-z ]+?)(?::|,|\. |\n)", prompt):
            defined.add(m.group(1).strip().lower())
        for name in named:
            if name not in defined:
                add("block", "MISSING_SUBJECT_DEF",
                    f"{label}: '{name}' appears in the prompt but no <Subject N> definition carries a reference",
                    "Attach that character's reference images to this segment and define them.")

        if attached_audio and not audio_defs:
            add("review", "AUDIO_ATTACHED_UNUSED",
                f"{label}: audio refs are attached but no <Audio N> definition uses them",
                "Define the timbre mapping or remove the unused audio.")

        if VIDEO_DEF.search(prompt) and not clips:
            add("block", "NO_VIDEO_ANCHOR",
                f"{label}: prompt refers to <Video N> but the timeline has no videoClips",
                "Attach a preceding-shot clip as a continuity reference, or remove the <Video N> line.")

        start = int(seg.get("startFrame", 0))
        end = int(seg.get("endFrame", 0))
        length = end - start
        if segments_are_finite(segments) and not (124 <= length <= 362 and (length - 5) % 17 == 0):
            add("block", "BAD_SEGMENT_LENGTH",
                f"{label}: {length} frames is outside 124-362 or not 5+17n",
                "Resnap the segment length to the 5+17n grid inside the trained range.")
        if previous is not None:
            overlap = int(previous.get("endFrame", 0)) - start
            if not valid_overlap(overlap):
                add("block", "TRANSITION_OVERLAP_INVALID",
                    f"{label}: overlaps the previous segment by {overlap} frames; "
                    "allowed overlap is 0, 1 or 5+17n",
                    "Resnap the segment boundary; a partial overlap corrupts the seam.")
        previous = seg

    return findings


def valid_overlap(value: int) -> bool:
    return value in (0, 1) or (value >= 5 and (value - 5) % 17 == 0)


def segments_are_finite(segments: list) -> bool:
    return bool(segments) and all(isinstance(s.get("startFrame"), int) and isinstance(s.get("endFrame"), int)
                                  for s in segments)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("timeline", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        timeline = load_timeline(args.timeline)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)[:500]}, ensure_ascii=False))
        return 3
    findings = check(timeline)
    blocks = [f for f in findings if f["severity"] == "block"]
    status = "block" if blocks else ("review" if findings else "pass")
    report = {"status": status, "segments": len(((timeline.get("segmentConfig") or {}).get("segments") or [])),
              "findings": findings}
    if args.json:
        print(json.dumps(report, ensure_ascii=False))
    else:
        print(json.dumps({"status": status, "findings": len(findings)}, ensure_ascii=False))
        for f in findings:
            print(f"[{f['severity']}] {f['code']}: {f['detail']}")
    return 1 if blocks else (2 if findings else 0)


if __name__ == "__main__":
    sys.exit(main())
