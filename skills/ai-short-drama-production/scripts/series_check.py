#!/usr/bin/env python3
"""Check a series bible and episode outlines for structural and cross-episode consistency.

This validates the contract layer only: schema completeness, entity registration,
entry/exit state consistency, thread ordering, and locked-appearance discipline.
It does not judge whether the story, episode hooks, or state changes are good.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ENTITY_KINDS = {"character", "location", "prop"}
BEAT_FIELDS = ("hook", "want", "obstacle", "strategy_shift", "power_turn", "cost")
OUTLINE_FIELDS = ("episode_no", "title", "premise", "entry_state", "exit_state",
                  "entities_used", "entity_deltas", "threads")


def _add(findings, code, severity, location, advice):
    findings.append({"code": code, "severity": severity, "location": location,
                     "repair_direction": advice})


def check_bible(bible, findings):
    if not isinstance(bible, dict):
        _add(findings, "SERIES_BIBLE_INVALID", "block", "/bible",
             "The bible must be a JSON object.")
        return {}, {}, {}
    if not bible.get("series_id"):
        _add(findings, "SERIES_ID_MISSING", "block", "/bible/series_id",
             "Give the bible a stable series_id.")
    entities = {}
    for item in bible.get("entities") or []:
        eid, kind = item.get("id"), item.get("kind")
        if not eid:
            _add(findings, "SERIES_ENTITY_NO_ID", "block", "/bible/entities",
                 "Every entity needs an id.")
            continue
        if eid in entities:
            _add(findings, "SERIES_DUPLICATE_ENTITY", "block", eid,
                 "Register each entity once; merge duplicates.")
        entities[eid] = item
        if kind not in ENTITY_KINDS:
            _add(findings, "SERIES_ENTITY_KIND", "block", eid,
                 "kind must be one of " + ", ".join(sorted(ENTITY_KINDS)) + ".")
        if kind == "character" and item.get("locked") and not item.get("appearance"):
            _add(findings, "SERIES_LOCKED_NO_APPEARANCE", "block", eid,
                 "A locked character needs a canonical appearance description.")
    thread_specs = {}
    for thread in bible.get("threads") or []:
        tid = thread.get("id")
        if not tid:
            _add(findings, "SERIES_THREAD_NO_ID", "block", "/bible/threads",
                 "Every plot thread needs an id.")
            continue
        opened, closed = thread.get("opened_in"), thread.get("closed_in")
        if not isinstance(opened, int) or isinstance(opened, bool) or opened < 1:
            _add(findings, "SERIES_THREAD_NO_ORIGIN", "block", tid,
                 "opened_in must be a positive episode number.")
            continue
        if closed is not None and (not isinstance(closed, int) or isinstance(closed, bool)
                                   or closed < opened):
            _add(findings, "SERIES_THREAD_ORDER", "block", tid,
                 "closed_in must be an episode number no earlier than opened_in.")
            continue
        if tid in thread_specs:
            _add(findings, "SERIES_THREAD_DUPLICATE", "block", tid,
                 "Register each thread once.")
        thread_specs[tid] = thread
    world = {}
    for item in bible.get("initial_state") or []:
        if isinstance(item, dict) and item.get("entity") and item.get("key") is not None:
            world[(item["entity"], item["key"])] = item.get("value")
    return entities, world, thread_specs


def check_outlines(outlines, entities, findings, world, thread_specs):
    episodes = sorted(outlines, key=lambda e: e.get("episode_no", 0))
    seen = set()
    departed = set()
    open_threads = set()
    for outline in episodes:
        no = outline.get("episode_no")
        loc = f"episode {no}"
        if not isinstance(no, int) or isinstance(no, bool) or no < 1:
            _add(findings, "SERIES_EPISODE_ORDER", "block", str(no),
                 "episode_no must be a positive integer.")
            continue
        if no in seen:
            _add(findings, "SERIES_EPISODE_ORDER", "block", loc,
                 "episode_no must be unique.")
        seen.add(no)
        for tid, spec in thread_specs.items():
            if spec["opened_in"] == no:
                open_threads.add(tid)

        for field in OUTLINE_FIELDS:
            if field not in outline:
                _add(findings, "EPISODE_OUTLINE_INCOMPLETE", "block", f"{loc}/{field}",
                     "Declare the field even if its value is empty.")
        for field in BEAT_FIELDS:
            if not str(outline.get(field) or "").strip():
                _add(findings, "EPISODE_OUTLINE_INCOMPLETE", "block", f"{loc}/{field}",
                     "Write an observable " + field + ", not a placeholder.")
        if not str(outline.get("cliffhanger") or outline.get("resolution") or "").strip():
            _add(findings, "EPISODE_OUTLINE_INCOMPLETE", "block", f"{loc}/ending",
                 "Declare a cliffhanger or a local resolution suited to the episode form.")

        deltas = outline.get("entity_deltas") or {}
        returns = set(deltas.get("returns") or [])
        for eid in sorted(returns - (departed & entities.keys())):
            _add(findings, "SERIES_RETURN_INVALID", "block", f"{loc}/{eid}",
                 "A return must name a registered, previously departed entity.")
        departed -= returns
        for item in deltas.get("introduces") or []:
            if not isinstance(item, dict):
                _add(findings, "SERIES_INTRODUCE_INCOMPLETE", "block", f"{loc}/entity_deltas",
                     "Each introduced entity must be an object with id and kind.")
        introduces = {d.get("id"): d for d in deltas.get("introduces") or [] if isinstance(d, dict)}
        for iid, item in introduces.items():
            if not iid or item.get("kind") not in ENTITY_KINDS:
                _add(findings, "SERIES_INTRODUCE_INCOMPLETE", "block", f"{loc}/{iid}",
                     "Each introduced entity needs an id and a valid kind.")
            elif iid not in entities:
                _add(findings, "SERIES_INTRODUCTION_UNREGISTERED", "review", f"{loc}/{iid}",
                     "Register the introduced entity in the bible and create its asset "
                     "passport before producing this episode.")

        used = set(outline.get("entities_used") or [])
        for field, items in (("entry_state", outline.get("entry_state") or []),
                             ("exit_state", outline.get("exit_state") or [])):
            for item in items:
                if isinstance(item, dict) and item.get("entity"):
                    used.add(item["entity"])
                else:
                    _add(findings, "SERIES_STATE_ITEM", "block", f"{loc}/{field}",
                         "Each state item needs entity, key and value.")
        for eid in sorted(used - set(introduces) - entities.keys()):
            _add(findings, "SERIES_ENTITY_UNREGISTERED", "block", f"{loc}/{eid}",
                 "Register the entity in the bible or declare it in entity_deltas.introduces.")
        for eid in sorted(used & departed):
            _add(findings, "SERIES_DEPARTED_USED", "block", f"{loc}/{eid}",
                 "The entity departed in an earlier episode; reverse the departure or "
                 "restate it as a return in entity_deltas.")
        for eid in sorted(set(deltas.get("departs") or []) - used - set(entities)):
            _add(findings, "SERIES_DEPART_UNKNOWN", "review", f"{loc}/{eid}",
                 "A departure usually names an entity registered or used in the series.")

        known = {**entities, **{i: v for i, v in introduces.items() if i}}
        for item in outline.get("entry_state") or []:
            if not isinstance(item, dict):
                continue
            eid, key, value = item.get("entity"), item.get("key"), item.get("value")
            if not eid or key is None:
                continue
            if key == "appearance" and (known.get(eid) or {}).get("locked"):
                _add(findings, "SERIES_LOCKED_APPEARANCE_CHANGE", "block", f"{loc}/{eid}",
                     "Locked appearance changes only through a registered state variant, "
                     "not an entry-state assert.")
            state_key = (eid, key)
            if state_key in world and world[state_key] != value:
                _add(findings, "SERIES_ENTRY_STATE_MISMATCH", "block",
                     f"{loc}/{eid}.{key}",
                     f"Accumulated state is {world[state_key]!r}; the outline asserts "
                     f"{value!r}. Fix the outline or record the off-page change in "
                     "the previous episode's exit_state.")
        for item in outline.get("exit_state") or []:
            if isinstance(item, dict):
                eid, key = item.get("entity"), item.get("key")
                if eid and key is not None:
                    if key == "appearance" and (known.get(eid) or {}).get("locked"):
                        _add(findings, "SERIES_LOCKED_APPEARANCE_CHANGE", "block",
                             f"{loc}/{eid}",
                             "Locked appearance changes only through a registered state "
                             "variant, not an exit-state write.")
                    world[(eid, key)] = item.get("value")

        threads = outline.get("threads") or {}
        for spec in threads.get("opens") or []:
            tid = spec.get("id") if isinstance(spec, dict) else spec
            declared = thread_specs.get(tid, {})
            if declared and declared["opened_in"] != no:
                _add(findings, "SERIES_THREAD_ORDER", "block", f"{loc}/{tid}",
                     "The opening conflicts with the registered opening episode.")
            if tid in open_threads and declared.get("opened_in") != no:
                _add(findings, "SERIES_THREAD_REOPEN", "review", f"{loc}/{tid}",
                     "The thread is already open; confirm it is a deliberate reactivation.")
            if tid:
                open_threads.add(tid)
        for tid in threads.get("closes") or []:
            declared = thread_specs.get(tid, {})
            if declared.get("closed_in") is not None and declared["closed_in"] != no:
                _add(findings, "SERIES_THREAD_ORDER", "block", f"{loc}/{tid}",
                     "The closure conflicts with the registered closing episode.")
            if tid and tid not in open_threads:
                _add(findings, "SERIES_THREAD_CLOSE_UNOPENED", "block", f"{loc}/{tid}",
                     "A thread can close only if an earlier episode opened it.")
            open_threads.discard(tid)
        for tid, spec in thread_specs.items():
            if spec.get("closed_in") == no:
                open_threads.discard(tid)

        departed |= set(deltas.get("departs") or [])
        entities.update({i: v for i, v in introduces.items() if i})

    expected = list(range(1, len(seen) + 1))
    if seen and sorted(seen) != expected[:len(seen)]:
        _add(findings, "SERIES_EPISODE_GAP", "review", "/episodes",
             "episode_no values are not contiguous from 1; confirm the numbering is intended.")
    return len(episodes)


def result(findings, episodes_checked):
    return {"status": "BLOCK" if any(f["severity"] == "block" for f in findings)
            else "REVIEW_REQUIRED",
            "episodes_checked": episodes_checked,
            "narrative_review": "not_performed", "findings": findings}


def history_digest(history):
    encoded = json.dumps(history, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def audit(bible, outlines, expected_history_sha256=None):
    findings = []
    entities, world, thread_specs = check_bible(bible, findings)
    history = bible.get("episodes", []) if isinstance(bible, dict) else []
    if not isinstance(history, list):
        _add(findings, "SERIES_HISTORY_INVALID", "block", "/bible/episodes",
             "History must be a list of complete episode outlines.")
        history = []
    pin = history_digest(history)
    if expected_history_sha256 is not None and pin != expected_history_sha256:
        _add(findings, "SERIES_HISTORY_HASH_MISMATCH", "block", "/bible/episodes",
             "Restore the reviewed history version or explicitly review the change.")
    combined = {}
    for origin, records in (("history", history), ("outlines", outlines)):
        if not isinstance(records, list):
            _add(findings, "SERIES_HISTORY_INVALID", "block", origin,
                 "Supply a list of complete episode outlines.")
            continue
        local_seen = set()
        for record in records:
            no = record.get("episode_no") if isinstance(record, dict) else None
            if not isinstance(no, int) or isinstance(no, bool) or no < 1:
                _add(findings, "SERIES_EPISODE_ORDER", "block", origin,
                     "Every record must be an object with a positive episode_no.")
                continue
            if no in local_seen:
                _add(findings, "SERIES_EPISODE_ORDER", "block", f"{origin}/{no}",
                     "Duplicate episode numbers are not allowed.")
            local_seen.add(no)
            if no in combined and combined[no] != record:
                _add(findings, "SERIES_HISTORY_CONFLICT", "block", f"episode {no}",
                     "Do not replace recorded history silently; review a revised history "
                     "and recheck all affected episodes.")
                continue
            combined[no] = record
    requested = [item["episode_no"] for item in outlines if isinstance(item, dict)
                 and isinstance(item.get("episode_no"), int)
                 and not isinstance(item["episode_no"], bool) and item["episode_no"] > 0] \
        if isinstance(outlines, list) else []
    if requested and any(no not in combined for no in range(1, min(requested))):
        _add(findings, "SERIES_HISTORY_INCOMPLETE", "block", "/bible/episodes",
             "Incremental checks require every preceding episode; do not reset to initial_state.")
    count = check_outlines(list(combined.values()), entities, findings, world, thread_specs)
    return {**result(findings, count), "history_sha256": pin,
            "history_episodes_replayed": len(history),
            "history_review": "not_performed"}


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bible", required=True, help="series bible JSON")
    parser.add_argument("--history-sha256", help="Expected hash of the recorded episode history")
    parser.add_argument("--outlines", required=True, nargs="+",
                        help="episode outline JSON files or a directory containing them")
    args = parser.parse_args(argv)
    try:
        bible = _load_json(args.bible)
        files = []
        for item in args.outlines:
            path = Path(item)
            files.extend(sorted(path.glob("*.json")) if path.is_dir() else [path])
        outlines = [_load_json(f) for f in files]
        report = audit(bible, outlines, expected_history_sha256=args.history_sha256)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except (OSError, json.JSONDecodeError, AttributeError, TypeError) as exc:
        print(json.dumps({"status": "INVALID_INPUT", "error": str(exc)}, ensure_ascii=False))
        return 2
    return 1 if report["status"] == "BLOCK" else 0


if __name__ == "__main__":
    sys.exit(main())
