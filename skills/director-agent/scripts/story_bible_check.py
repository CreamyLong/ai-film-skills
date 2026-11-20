#!/usr/bin/env python3
"""Story-bible completeness gate: block episode writing until every appearing
character has a profile and every antagonist has a motive.

Inputs are plain JSON so any project's bible can be normalised into them:
  --bible      {"characters": {name: {"profile": str, "role": "protagonist|
               antagonist|support", "motive": str, "resources": str,
               "means": str, "asset_id": str}}}
  --appearances [{"episode": "EP014", "character": "周启明", "speaks": true}]

Checks (all block unless noted):
  1. every character that appears or speaks has a profile;
  2. every antagonist carries motive + resources + means;
  3. every appearing character has a locked asset_id;
  4. the cast has at least one protagonist and one antagonist (review if not).

Exit codes: 0 pass, 1 block, 2 review, 3 error.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def check(bible: dict, appearances: list[dict]) -> list[dict]:
    characters = bible.get("characters", {})
    findings = []

    def add(severity, code, who, detail):
        findings.append({"severity": severity, "code": code,
                         "character": who, "detail": detail})

    appearing = {}
    for app in appearances:
        name = app.get("character")
        if name:
            appearing.setdefault(name, []).append(app.get("episode", "?"))

    for name, eps in sorted(appearing.items()):
        entry = characters.get(name)
        if entry is None:
            add("block", "MISSING_PROFILE", name,
                f"appears in {sorted(set(eps))} but has no entry in the story bible")
            continue
        if not str(entry.get("profile", "")).strip():
            add("block", "EMPTY_PROFILE", name,
                f"appears in {sorted(set(eps))} but the profile text is empty")
        if entry.get("role") == "antagonist":
            for field in ("motive", "resources", "means"):
                if not str(entry.get(field, "")).strip():
                    add("block", f"ANTAGONIST_NO_{field.upper()}", name,
                        f"antagonist without {field}; an opponent with no {field} "
                        "will surface as a contrivance later")
        if not str(entry.get("asset_id", "")).strip():
            add("block", "NO_LOCKED_ASSET", name,
                "no locked character asset id; production will improvise the face")

    roles = {c.get("role") for c in characters.values()}
    if "antagonist" not in roles:
        add("review", "NO_ANTAGONIST", "-", "cast has no declared antagonist")
    if "protagonist" not in roles:
        add("review", "NO_PROTAGONIST", "-", "cast has no declared protagonist")
    return findings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bible", required=True, type=Path)
    parser.add_argument("--appearances", required=True, type=Path,
                        help="JSON list, or JSONL with one appearance per line")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        bible = json.loads(args.bible.read_text(encoding="utf-8"))
        raw = args.appearances.read_text(encoding="utf-8").strip()
        appearances = json.loads(raw) if raw.startswith("[") else \
            [json.loads(line) for line in raw.splitlines() if line.strip()]
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)[:400]}, ensure_ascii=False))
        return 3
    findings = check(bible, appearances)
    blocks = [f for f in findings if f["severity"] == "block"]
    status = "block" if blocks else ("review" if findings else "pass")
    report = {"status": status, "findings": findings,
              "characters": len(bible.get("characters", {})),
              "appearances": len(appearances)}
    print(json.dumps(report, ensure_ascii=False, indent=2 if not args.json else None))
    return 1 if blocks else (2 if findings else 0)


if __name__ == "__main__":
    sys.exit(main())
