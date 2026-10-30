#!/usr/bin/env python3
"""Check declared shot handoffs and exact dialogue mapping without calling a model."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

SCHEMA = "film-skills.shot-preflight/v1"
IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MAX_BYTES = 2_000_000


class InputError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise InputError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def identifier(value):
    return isinstance(value, str) and bool(IDENTIFIER.fullmatch(value))


def object_fields(value, allowed, required, location):
    require(isinstance(value, dict), f"{location}: expected object")
    require(set(value) <= allowed and required <= set(value), f"{location}: invalid fields")


def unique_json(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def audit(data):
    object_fields(data, {"schema", "tracked_items", "shots"},
                  {"schema", "tracked_items", "shots"}, "root")
    require(data["schema"] == SCHEMA, "unsupported schema")
    items = data["tracked_items"]
    require(isinstance(items, list) and all(identifier(x) for x in items)
            and len(set(items)) == len(items), "invalid tracked_items")
    shots = data["shots"]
    require(isinstance(shots, list) and bool(shots), "shots must be a nonempty list")
    findings = []
    hashes = []
    previous = None
    seen = set()

    def add(code, severity, shot_id, location, advice):
        findings.append({"code": code, "severity": severity, "shot_id": shot_id,
                         "location": location, "repair_direction": advice})

    for index, shot in enumerate(shots):
        loc = f"/shots/{index}"
        required = {"id", "duration_seconds", "prompt", "audio_route", "dialogue",
                    "entry_state", "exit_state"}
        allowed = required | {"audio_prompt", "speech_timing", "transition",
                              "entry_changes", "state_actions", "previous_tail_claim",
                              "initial_frame"}
        object_fields(shot, allowed, required, loc)
        sid = shot["id"]
        require(identifier(sid) and sid not in seen, f"{loc}: invalid or duplicate id")
        seen.add(sid)
        duration = shot["duration_seconds"]
        require(number(duration) and duration > 0, f"{loc}: invalid duration")
        require(text(shot["prompt"]), f"{loc}: prompt is required")
        hashes.append({"shot_id": sid, "prompt_sha256": hashlib.sha256(
            shot["prompt"].encode("utf-8")).hexdigest()})

        route = shot["audio_route"]
        require(route in ("native", "external", "silent"), f"{loc}: invalid audio_route")
        dialogue = shot["dialogue"]
        require(isinstance(dialogue, list), f"{loc}: dialogue must be a list")
        audio_prompt = shot.get("audio_prompt", "")
        require(isinstance(audio_prompt, str), f"{loc}: invalid audio_prompt")
        for dindex, line in enumerate(dialogue):
            object_fields(line, {"speaker", "text"}, {"speaker", "text"}, f"{loc}/dialogue/{dindex}")
            require(text(line["speaker"]) and text(line["text"]), f"{loc}: invalid dialogue")
            target = shot["prompt"] if route == "native" else audio_prompt
            if route == "silent" or line["text"] not in target:
                add("DIALOGUE_NOT_MAPPED", "block", sid, f"{loc}/dialogue/{dindex}",
                    "Map the exact line to the selected audio submission, or resolve the silent-audio conflict.")

        timing = shot.get("speech_timing")
        if dialogue and timing is None:
            add("SPEECH_TIMING_UNVERIFIED", "review", sid, f"{loc}/speech_timing",
                "Time a representative read or recording, including pauses, against its actual audio window.")
        if timing is not None:
            object_fields(timing, {"measured_seconds", "window_seconds", "basis", "cross_shot"},
                          {"measured_seconds", "window_seconds", "basis", "cross_shot"},
                          f"{loc}/speech_timing")
            measured, window = timing["measured_seconds"], timing["window_seconds"]
            require(number(measured) and measured >= 0 and (not dialogue or measured > 0)
                    and number(window) and window > 0
                    and text(timing["basis"]) and type(timing["cross_shot"]) is bool,
                    f"{loc}: invalid speech_timing")
            require(window <= duration or timing["cross_shot"],
                    f"{loc}: an extended audio window requires cross_shot")
            if timing["cross_shot"]:
                add("CROSS_SHOT_TIMING_UNVERIFIED", "review", sid, f"{loc}/speech_timing",
                    "Verify the complete audio window and overlap across the affected edited shots.")
            if measured > window:
                add("SPEECH_WINDOW_OVERRUN", "block", sid, f"{loc}/speech_timing",
                    "Re-time the delivery or propose an authorized longer or cross-shot window; do not drop lines.")

        for field in ("entry_state", "exit_state"):
            state = shot[field]
            require(isinstance(state, dict) and set(state) == set(items)
                    and all(value is None or text(value) for value in state.values()),
                    f"{loc}: {field} must cover tracked_items with text or null")
            for item, value in state.items():
                if value is None:
                    add("STATE_UNVERIFIED", "review", sid, f"{loc}/{field}/{item}",
                        "Verify this state from the source or leave the affected handoff unverified.")

        actions = shot.get("state_actions", {})
        require(isinstance(actions, dict) and set(actions) <= set(items)
                and all(text(value) for value in actions.values()), f"{loc}: invalid state_actions")
        for item in items:
            before, after = shot["entry_state"][item], shot["exit_state"][item]
            if before is not None and after is not None and before != after:
                evidence = actions.get(item)
                if not evidence or evidence not in shot["prompt"]:
                    add("STATE_ACTION_UNVERIFIED", "review", sid, f"{loc}/state_actions/{item}",
                        "Identify the actual submitted action or other verified evidence for this change.")

        claim = shot.get("previous_tail_claim", {})
        require(isinstance(claim, dict) and set(claim) <= set(items)
                and all(value is None or text(value) for value in claim.values()),
                f"{loc}: invalid previous_tail_claim")
        changes = shot.get("entry_changes", {})
        require(isinstance(changes, dict) and set(changes) <= set(items)
                and all(text(value) for value in changes.values()), f"{loc}: invalid entry_changes")
        if previous is None:
            if claim:
                add("PREVIOUS_TAIL_UNAVAILABLE", "review", sid, f"{loc}/previous_tail_claim",
                    "Compare the claim with the actual preceding shot before using it as a handoff.")
        else:
            transition = shot.get("transition")
            require(transition in ("continuous", "cut", "ellipsis"), f"{loc}: invalid transition")
            for item in items:
                old, new = previous["exit_state"][item], shot["entry_state"][item]
                if item in claim and claim[item] is not None and old is not None and claim[item] != old:
                    add("PREVIOUS_TAIL_MISMATCH", "block", sid, f"{loc}/previous_tail_claim/{item}",
                        "Correct the claimed prior tail using the preceding shot's actual exit state.")
                if old is not None and new is not None and old != new:
                    if item not in changes:
                        add("STATE_HANDOFF_UNEXPLAINED",
                            "block" if transition == "continuous" else "review",
                            sid, f"{loc}/entry_state/{item}",
                            "Locate or propose an authorized handoff, or document and verify the ellipsis.")
                    else:
                        add("STATE_HANDOFF_REQUIRES_REVIEW", "review", sid, f"{loc}/entry_changes/{item}",
                            "Verify the stated transition against the source and actual edited material.")
            old_frame, new_frame = previous.get("initial_frame"), shot.get("initial_frame")
            if transition == "continuous" and old_frame and old_frame == new_frame:
                add("CONTINUOUS_START_FRAME_REUSED", "review", sid, f"{loc}/initial_frame",
                    "Compare the previous generated ending with this start; the same original still is not its tail.")
        if "initial_frame" in shot:
            require(text(shot["initial_frame"]), f"{loc}: invalid initial_frame")
        previous = shot

    return {"schema": SCHEMA, "status": "BLOCK" if any(
        issue["severity"] == "block" for issue in findings) else "REVIEW_REQUIRED",
        "scope": "declared_structure_only", "semantic_review": "not_performed",
        "asset_review": "not_performed", "actual_model_submission_checked": False,
        "prompts": hashes, "findings": findings}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        with args.input.open("rb") as handle:
            raw = handle.read(MAX_BYTES + 1)
        require(len(raw) <= MAX_BYTES, "input too large")
        data = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_json,
                          parse_constant=lambda _: (_ for _ in ()).throw(InputError("invalid number")))
        result = audit(data)
        result["input_sha256"] = hashlib.sha256(raw).hexdigest()
    except (OSError, ValueError, UnicodeError, InputError, OverflowError) as exc:
        result = {"schema": SCHEMA, "status": "INVALID_INPUT",
                  "error": str(exc) if isinstance(exc, InputError) else "cannot read valid JSON",
                  "semantic_review": "not_performed"}
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 1 if result["status"] in ("BLOCK", "INVALID_INPUT") else 2


if __name__ == "__main__":
    sys.exit(main())
