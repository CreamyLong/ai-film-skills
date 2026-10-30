#!/usr/bin/env python3
"""Offline production ledger. Reviews are explicit attestations, not media analysis."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import uuid

SCHEMA = "film-skills.production-state/v1"
DOMAINS = {
    "source": ("coverage",), "screenplay": ("story",),
    "director": ("directing", "continuity"), "asset": ("asset",),
    "animatic": ("story", "pacing"), "keyframe": ("visual", "continuity"),
    "submission": ("semantic", "assets", "keyframes", "audio", "capability",
                   "authorization", "continuity"),
    "video": ("visual", "audio", "continuity"),
    "scene": ("picture", "sound", "continuity"),
    "film": ("story", "picture", "sound", "continuity", "delivery"),
}
MAX_FILE_BYTES = 8 * 1024**3


class StateError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise StateError(message)


def digest(value):
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_hash(path):
    path = Path(path)
    require(path.is_absolute(), "file path must be absolute")
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as handle:
        before = os.fstat(handle.fileno())
        require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= MAX_FILE_BYTES,
                "expected nonempty regular file within hashing limit")
        sha = hashlib.sha256()
        total = 0
        while chunk := handle.read(1024 * 1024):
            total += len(chunk)
            require(total <= MAX_FILE_BYTES, "file exceeds hashing limit")
            sha.update(chunk)
        after = os.fstat(handle.fileno())
        current = path.stat()
        signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
        require(signature(before) == signature(after) == signature(current),
                "file changed while hashing")
        return sha.hexdigest()


def load_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    with Path(path).open("rb") as handle:
        raw = handle.read(16_000_001)
    require(len(raw) <= 16_000_000, "JSON exceeds local limit")
    value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique,
                       parse_constant=lambda _: require(False, "nonfinite JSON"))
    require(isinstance(value, dict), "expected JSON object")
    return value


def read_state(path):
    state = load_json(path)
    require(state.get("schema") == SCHEMA, "unsupported state schema")
    require(isinstance(state.get("artifacts"), dict)
            and isinstance(state.get("jobs"), dict)
            and isinstance(state.get("events"), list), "invalid ledger")
    return state


@contextmanager
def transaction(path, initialize=False):
    path = Path(path)
    require(path.is_absolute() and path.parent.is_dir(), "existing absolute state parent required")
    lock = path.with_name(path.name + ".lock")
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise StateError("ledger busy; do not clear another writer's lock") from None
    temporary = None
    try:
        os.close(descriptor)
        if initialize:
            require(not path.exists(), "ledger already exists; initialization never overwrites")
            state = {"schema": SCHEMA, "artifacts": {}, "jobs": {}, "events": []}
        else:
            state = read_state(path)
        yield state
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(state, handle, ensure_ascii=False, sort_keys=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        lock.unlink()


def closure(state, artifact_id, trail=()):
    require(artifact_id not in trail, "dependency cycle")
    require(artifact_id in state["artifacts"], f"missing artifact: {artifact_id}")
    found = {artifact_id}
    for dependency in state["artifacts"][artifact_id]["dependencies"]:
        found.update(closure(state, dependency, trail + (artifact_id,)))
    return found


def problems(state, artifact_id, own_reviews=True, trail=()):
    require(artifact_id not in trail, "dependency cycle")
    item = state["artifacts"].get(artifact_id)
    if item is None:
        return [f"{artifact_id}: missing"]
    errors = []
    if item.get("stale"):
        errors.append(f"{artifact_id}: stale")
    if item["path"]:
        try:
            require(file_hash(item["path"]) == item["sha256"], "bytes changed")
        except (OSError, StateError) as exc:
            errors.append(f"{artifact_id}: {exc}")
    for dep, pin in item["dependencies"].items():
        current = state["artifacts"].get(dep)
        if current is None or current["fingerprint"] != pin:
            errors.append(f"{artifact_id}: dependency changed: {dep}")
        errors.extend(problems(state, dep, True, trail + (artifact_id,)))
    if own_reviews:
        for domain in DOMAINS[item["kind"]]:
            review = item["reviews"].get(domain, {})
            if (review.get("verdict") != "accepted"
                    or review.get("fingerprint") != item["fingerprint"]):
                errors.append(f"{artifact_id}: {domain} review required")
                continue
            try:
                require(file_hash(review["evidence"]) == review["evidence_sha256"],
                        "review evidence changed")
            except (OSError, StateError) as exc:
                errors.append(f"{artifact_id}: {domain}: {exc}")
    return sorted(set(errors))


def invalidate(state, artifact_id):
    affected = set()
    pending = {artifact_id}
    while pending:
        current = pending.pop()
        for aid, item in state["artifacts"].items():
            if aid != artifact_id and aid not in affected and current in item["dependencies"]:
                item["stale"], item["reviews"] = True, {}
                affected.add(aid)
                pending.add(aid)
    return sorted(affected)


def register(state, command):
    aid, kind = command["id"], command["kind"]
    require(isinstance(aid, str) and aid.strip() and kind in DOMAINS, "invalid artifact")
    data = command.get("data", {})
    path = command.get("path")
    require(isinstance(data, dict) and (path is not None or data), "path or data required")
    require(kind not in ("animatic", "keyframe", "video", "scene", "film") or path is not None,
            "media artifacts require an actual local file")
    sha = file_hash(path) if path is not None else None
    deps = command.get("dependencies", [])
    require(isinstance(deps, list) and len(deps) == len(set(deps)), "invalid dependencies")
    require(aid not in deps, "self dependency")
    pins = {}
    for dependency in deps:
        require(aid not in closure(state, dependency), "dependency cycle")
        pins[dependency] = state["artifacts"][dependency]["fingerprint"]
    content = {"kind": kind, "path": str(path) if path else None,
               "sha256": sha, "data": data, "dependencies": pins}
    fingerprint = digest(content)
    previous = state["artifacts"].get(aid)
    if previous and previous["fingerprint"] == fingerprint and not previous["stale"]:
        return {"id": aid, "changed": False, "fingerprint": fingerprint}
    require(not previous or previous["kind"] == kind, "artifact kind cannot change")
    state["events"].append({"action": "register", "id": aid, "previous": previous})
    state["artifacts"][aid] = {
        **content, "fingerprint": fingerprint, "stale": False, "reviews": {},
        "revision": previous["revision"] + 1 if previous else 1,
    }
    return {"id": aid, "changed": True, "fingerprint": fingerprint,
            "invalidated": invalidate(state, aid)}


def execute(state, command):
    action = command["action"]
    if action == "register":
        return register(state, command)
    if action == "status":
        ids = [command["id"]] if command.get("id") else sorted(state["artifacts"])
        return {"artifacts": {
            aid: {"ready": not (issues := problems(state, aid)), "problems": issues}
            for aid in ids
        }, "media_analysis_performed": False}
    if action == "review":
        aid, domain = command["id"], command["domain"]
        item = state["artifacts"][aid]
        require(domain in DOMAINS[item["kind"]], "invalid review domain")
        require(command["verdict"] in ("accepted", "rejected"), "invalid verdict")
        require(command.get("authority") in ("user", "delegated")
                and isinstance(command.get("reviewer"), str)
                and command["reviewer"].strip(), "explicit review authority required")
        if command["verdict"] == "accepted":
            require(not problems(state, aid, own_reviews=False),
                    "cannot accept changed files or unready dependencies")
        evidence = str(command["evidence"])
        review = {key: command[key] for key in ("verdict", "authority", "reviewer")}
        review.update(evidence=evidence, evidence_sha256=file_hash(evidence),
                      fingerprint=item["fingerprint"])
        state["events"].append({"action": "review", "id": aid, "domain": domain,
                                "previous": item["reviews"].get(domain)})
        item["reviews"][domain] = review
        return {"id": aid, "invalidated": invalidate(state, aid)}
    if action == "reserve":
        aid = command["id"]
        require(not problems(state, aid), "submission or dependencies need review")
        item = state["artifacts"][aid]
        require(item["kind"] == "submission", "expected submission artifact")
        request_hash = command["request_sha256"]
        require(request_hash == item["data"].get("request_sha256"), "request changed")
        for job in state["jobs"].values():
            if (job["submission"] == aid and job["fingerprint"] == item["fingerprint"]
                    and job["status"] != "failed"):
                raise StateError("attempt already exists; reconcile it instead of resubmitting")
        attempt = uuid.uuid4().hex
        state["jobs"][attempt] = {
            "submission": aid, "fingerprint": item["fingerprint"],
            "request_sha256": request_hash, "status": "reserved",
            "provider_job_id": None, "receipts": [],
        }
        return {"attempt": attempt}
    if action == "receipt":
        job = state["jobs"][command["attempt"]]
        status = command["status"]
        transitions = {
            "reserved": {"submitted", "failed", "unknown"},
            "submitted": {"completed", "failed", "unknown"},
            "unknown": {"submitted", "completed", "failed", "unknown"},
            "completed": set(), "failed": set(),
        }
        require(status in transitions[job["status"]], "invalid job transition")
        provider_id = command.get("provider_job_id")
        require(provider_id is None or isinstance(provider_id, str) and provider_id.strip(),
                "invalid provider job id")
        require(not job["provider_job_id"] or provider_id == job["provider_job_id"],
                "provider job id changed")
        require(status not in ("submitted", "completed") or provider_id,
                "provider job id required")
        receipt = str(command["path"])
        job["receipts"].append({"path": receipt, "sha256": file_hash(receipt),
                                 "status": status})
        job.update(status=status, provider_job_id=provider_id)
        return {"attempt": command["attempt"], "status": status}
    if action == "bind":
        job = state["jobs"][command["attempt"]]
        require(job["status"] == "completed", "job not completed")
        require(job["provider_job_id"] == command["provider_job_id"], "wrong result job")
        source = state["artifacts"][job["submission"]]
        require(source["fingerprint"] == job["fingerprint"]
                and not problems(state, job["submission"]), "submission became stale")
        require(job["receipts"], "missing completed receipt")
        receipt = job["receipts"][-1]
        require(file_hash(receipt["path"]) == receipt["sha256"], "result receipt changed")
        result = register(state, {
            "id": command["id"], "kind": "video", "path": command["path"],
            "dependencies": [job["submission"]],
            "data": {"attempt": command["attempt"], "provider_job_id": job["provider_job_id"],
                     "request_sha256": job["request_sha256"],
                     "receipt": receipt},
        })
        result["media_review_required"] = True
        return result
    raise StateError("unknown action")


def apply(path, command):
    with transaction(path, initialize=command["action"] == "init") as state:
        result = {"initialized": True} if command["action"] == "init" else execute(state, command)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--command", required=True, type=Path,
                        help="JSON action; never put private values in shell arguments")
    args = parser.parse_args(argv)
    try:
        result = apply(args.state.resolve(), load_json(args.command))
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as exc:
        print(json.dumps({"status": "BLOCK", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
