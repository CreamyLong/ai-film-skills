#!/usr/bin/env python3
"""Static shot-contract preflight for H3-style prompt sets.

Catches the structural failures that cost whole re-renders before the GPU is
used: reference/picture mismatches, alternating speakers in one shot,
dialogue plus prop action in one shot, information-bearing text props in
close-up, unanchored foreground people, and a missing environment anchor.

This is a planning check, not visual approval and not a model call.

Exit codes: 0 pass, 1 block, 2 review, 3 error.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

PICTURE = re.compile(r"<Picture (\d+)>")
SPEAKER = re.compile(r"<Subject (\d+)>[^\n<]*?says,\s*<d>")
SUBJECT_DEF = re.compile(r"<Subject (\d+)> \(S\d\)(?:,| is)?\s*([^:\n.]+)")
ISOLATES = re.compile(r"<Picture (\d+)>[^\n]*?\bisolates\b", re.I)
SHOULDER = re.compile(r"\bover ([A-Z][A-Za-z]*(?: [A-Z][A-Za-z]+)?)'s shoulder\b")
PROP = re.compile(
    r"\b(?:open |closed )?(file|folder|document|ledger|booklet|letter|newspaper|"
    r"diagram|blueprint|poster|notice|sign|screen|phone)\b", re.I)
TEXT_FOCUS = re.compile(
    r"\b(?:close-up|insert|fills? the frame|holds? (?:it|the [a-z ]+) up|"
    r"title|cover|page|headline|label|print(?:ed)?|reads?|reading)\b", re.I)
DIALOGUE_ACTION = re.compile(
    r"\b(?:opens? the (?:drawer|folder|file|book|box|case|envelope)|"
    r"pulls? (?:open|the drawer)|takes? out|lifts?|raises?|throws?|"
    r"sets? (?:it|the \w+)|places?|flips?|turns? (?:a |the )?pages?|"
    r"hands? (?:it|the \w+)|slides? (?:it|the \w+)|picks? up)\b", re.I)
SPACE = re.compile(
    r"\b(?:interior|exterior|room|door|doorway|table|wall|street|office|"
    r"apartment|warehouse|corridor|hallway|kitchen|bedroom)\b", re.I)
CLOSEUP = re.compile(r"\b(?:close-up|medium close-up|insert|detail shot)\b", re.I)


def picture_refs(shot: dict) -> list[dict]:
    return sorted(shot.get("refs", []), key=lambda r: int(r.get("tag", 0)))


def audit_shot(shot: dict) -> list[dict]:
    sid = str(shot.get("shot", "?"))
    prompt = shot.get("prompt", "")
    refs = picture_refs(shot)
    findings: list[dict] = []

    def add(severity: str, code: str, detail: str, fix: str) -> None:
        findings.append({"shot": sid, "severity": severity, "code": code,
                         "detail": detail, "fix": fix})

    numbers = {int(n) for n in PICTURE.findall(prompt)}
    if numbers and refs and max(numbers) != len(refs):
        add("block", "PICTURE_COUNT_MISMATCH",
            f"prompt uses <Picture {max(numbers)}> but {len(refs)} references are attached",
            "Renumber <Picture N> to match the attached reference order, and remove stale lines.")
    if numbers and not refs:
        add("block", "PICTURE_WITHOUT_REFS",
            "prompt refers to <Picture N> but no references are attached",
            "Attach the referenced images or remove the picture block.")

    for match in ISOLATES.finditer(prompt):
        index = int(match.group(1)) - 1
        if 0 <= index < len(refs):
            ref = refs[index]
            stem = Path(ref.get("file", "")).stem.lower()
            role = str(ref.get("role", "")).lower()
            if role in {"identity", "character"} or any(
                    word in stem for word in ("hero", "face", "turnaround", "grid", "expression")):
                add("block", "DETAIL_REF_IS_PORTRAIT",
                    f"<Picture {index + 1}> is declared as a detail/isolate but is a full portrait "
                    f"({Path(ref.get('file', '')).name})",
                    "Remove the detail claim and let the face reference carry identity; never call a "
                    "full portrait an isolate.")

    speakers = sorted({int(n) for n in SPEAKER.findall(prompt)})
    if len(speakers) > 1:
        add("review", "ALTERNATING_SPEAKERS",
            f"one shot contains dialogue from {len(speakers)} speakers ({speakers})",
            "Split into one shot per speaker (single visible mouth per shot) and edit them together.")

    body = prompt.split("detailed_description:", 1)[-1]
    if speakers and DIALOGUE_ACTION.search(body):
        action = DIALOGUE_ACTION.search(body).group(0)
        add("block", "DIALOGUE_PLUS_PROP_ACTION",
            f"the same shot asks for dialogue and a prop action ('{action}')",
            "Split: one shot speaks, another performs the prop action; or remove the action from the "
            "speaking shot.")

    prop = PROP.search(body)
    if prop and (TEXT_FOCUS.search(body) or CLOSEUP.search(body)):
        severity = "block" if re.search(
            r"\b(?:open (?:the )?(?:file|folder|document|booklet|ledger)|"
            r"holds? (?:it|the \w+) up|title|cover|headline|reads?|reading|page)\b",
            body, re.I) else "review"
        add(severity, "TEXT_PROP_IN_CLOSEUP",
            f"'{prop.group(0)}' is focal in a close-up/insert; generated Chinese glyphs will be gibberish",
            "Keep the prop closed, face-down, out of frame or out of focus; use a clean still insert "
            "for readable information.")

    if SPACE.search(body) and not any(
            "scene" in str(r.get("file", "")).lower() or str(r.get("role", "")).lower() == "environment"
            for r in refs) and not shot.get("video_refs"):
        add("block", "MISSING_ENVIRONMENT_ANCHOR",
            "the description names a room/space but no environment reference or video reference is attached",
            "Attach the scene reference; without it the model invents a different room.")

    known_names = {m.group(2).strip().split()[0] for m in SUBJECT_DEF.finditer(prompt)
                   if m.group(2).strip()}
    for match in SHOULDER.finditer(body):
        name = match.group(1)
        if name.split()[0] not in known_names:
            add("block", "UNANCHORED_FOREGROUND_PERSON",
                f"'{name}' fills the foreground but has no subject definition or reference",
                "Either add that character's locked reference or remove the foreground person.")

    return findings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompts", required=True, type=Path,
                        help="shot prompt JSON with a top-level 'shots' list")
    parser.add_argument("--shots", default="",
                        help="comma-separated shot ids; default all")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        data = json.loads(args.prompts.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)[:500]}, ensure_ascii=False))
        return 3
    shots = data.get("shots") if isinstance(data, dict) else data
    if not isinstance(shots, list):
        print(json.dumps({"status": "ERROR", "error": "no shots list"}, ensure_ascii=False))
        return 3
    wanted = {s for s in args.shots.split(",") if s}
    if wanted:
        shots = [s for s in shots if str(s.get("shot")) in wanted]

    findings: list[dict] = []
    for shot in shots:
        findings.extend(audit_shot(shot))
    blocks = [f for f in findings if f["severity"] == "block"]
    status = "block" if blocks else "pass"
    report = {"status": status, "prompts": str(args.prompts),
              "shots": len(shots), "findings": findings}
    out = args.out or args.prompts.with_name(args.prompts.stem + "_contract_check.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False))
    else:
        print(json.dumps({"status": status, "shots": len(shots),
                          "block": len(blocks), "report": str(out)}, ensure_ascii=False))
        for f in findings:
            print(f"[{f['severity']}] {f['shot']} {f['code']}: {f['detail']}")
    return 1 if blocks else 0


if __name__ == "__main__":
    sys.exit(main())
