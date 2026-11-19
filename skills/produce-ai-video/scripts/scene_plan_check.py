#!/usr/bin/env python3
"""Validate a scene-first production plan before any generation.

A plan is one episode with scenes; each scene has ambience and shots. The
checker blocks plans where continuity has no enforceable fields: missing env
reference, off-screen speaker without a closed-lip listener, visible speech
without a reference/locked route, or boundaries without exit/entry states.

Exit 0 = no blocker, 1 = blocker, 2 = input error. It does not generate media
and does not prove the plan is dramatically good.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SIZES = {"ECU", "CU", "MCU", "MS", "MW", "WS", "EWS", "OTS", "TWO"}
ROUTES = {"reference", "locked", "tts", "silent"}


def blocker(message: str) -> dict:
    return {"severity": "blocker", "message": message}


def warning(message: str) -> dict:
    return {"severity": "warning", "message": message}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2

    findings: list[dict] = []
    scenes = plan.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        print(json.dumps({"status": "ERROR", "error": "plan.scenes must be a non-empty list"},
                         ensure_ascii=False))
        return 2

    seen_scenes = set()
    for scene in scenes:
        sid = scene.get("id")
        if not sid or sid in seen_scenes:
            findings.append(blocker(f"scene id missing or duplicated: {sid!r}"))
        seen_scenes.add(sid)
        ambience = scene.get("ambience") or {}
        if not (ambience.get("source") or ambience.get("description")):
            findings.append(blocker(f"scene {sid}: no ambience source or description"))
        shots = scene.get("shots") or []
        if not shots:
            findings.append(blocker(f"scene {sid}: no shots"))
            continue

        envs = set()
        previous = None
        for shot in shots:
            name = shot.get("id")
            label = f"scene {sid} shot {name}"
            size = shot.get("size")
            if size not in SIZES:
                findings.append(blocker(f"{label}: invalid or missing size {size!r}"))
            subject = shot.get("subject")
            if not subject:
                findings.append(blocker(f"{label}: missing subject"))
            env = shot.get("env_ref")
            if not env:
                findings.append(blocker(f"{label}: missing env_ref (invented backgrounds follow)"))
            else:
                envs.add(env)
            if not shot.get("entry") or not shot.get("exit"):
                findings.append(blocker(f"{label}: missing entry/exit state"))

            speaker = shot.get("speaker")
            on_screen = shot.get("speaker_on_screen")
            route = shot.get("line_source")
            line = (shot.get("line") or "").strip()
            if speaker:
                if route not in ROUTES:
                    findings.append(blocker(f"{label}: speaker without line_source route"))
                if on_screen is True:
                    refs = " ".join(shot.get("char_refs") or [])
                    if speaker.split()[0].lower() not in refs.lower():
                        findings.append(blocker(
                            f"{label}: on-screen speaker {speaker!r} has no face ref"))
                    if route not in {"reference", "locked"}:
                        findings.append(blocker(
                            f"{label}: visible speech must use reference or locked, not {route!r}"))
                    if not line:
                        findings.append(blocker(f"{label}: visible speaker has no line text"))
                elif on_screen is False:
                    if shot.get("listener_lips") != "closed":
                        findings.append(blocker(
                            f"{label}: off-screen speech needs listener_lips=closed"))
                    if not shot.get("listener"):
                        findings.append(blocker(f"{label}: off-screen speech needs a listener"))
                    if line and not shot.get("sound_events"):
                        findings.append(warning(
                            f"{label}: off-screen line is not registered in sound_events"))
                else:
                    findings.append(blocker(f"{label}: speaker_on_screen must be true/false"))

            if previous is not None:
                if previous.get("exit") and shot.get("entry"):
                    pass
                if previous.get("env_ref") and env and previous["env_ref"] != env:
                    findings.append(blocker(
                        f"{label}: env_ref differs from previous shot in the same scene"))
                if not shot.get("transition_in"):
                    findings.append(warning(f"{label}: missing transition_in"))
            previous = shot

        if len(envs) > 1:
            findings.append(blocker(f"scene {sid}: shots use {len(envs)} different env_refs"))

    blockers = [item for item in findings if item["severity"] == "blocker"]
    report = {"status": "BLOCKED" if blockers else "PASS",
              "blockers": len(blockers), "findings": findings}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not args.json:
        for item in findings:
            print(f"{item['severity'].upper()}: {item['message']}", file=sys.stderr)
    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
