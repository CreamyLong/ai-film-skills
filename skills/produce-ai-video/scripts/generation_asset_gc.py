#!/usr/bin/env python3
"""Dispose of reviewed, unreferenced generated candidate media safely.

The default is a dry-run. Only files explicitly listed in a manifest with an
eligible review status and a matching SHA-256 can be acted on. The tool never
infers rejection from a filename and never scans a directory for deletion.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

ELIGIBLE = {"rejected", "superseded", "failed_partial"}
MEDIA = re.compile(
    r"[A-Za-z0-9_./\-\u4e00-\u9fff]+\."
    r"(?:mp4|mov|mkv|webm|png|jpe?g|wav|mp3|aac|flac)", re.I)
MEDIA_SUFFIX = re.compile(
    r"\.(?:mp4|mov|mkv|webm|png|jpe?g|wav|mp3|aac|flac)$", re.I)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def under(root: Path, path: Path) -> bool:
    return path == root or root in path.parents


def resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return (path if path.is_absolute() else root / path).resolve()


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)


def media_references(files: list[Path], root: Path) -> set[Path]:
    found: set[Path] = set()
    for ref in files:
        text = ref.read_text(encoding="utf-8")
        try:
            values = list(strings(json.loads(text)))
        except json.JSONDecodeError:
            values = MEDIA.findall(text)
        for value in values:
            exact = value.strip() if MEDIA_SUFFIX.search(value.strip()) else None
            for match in ([exact] if exact else MEDIA.findall(value)):
                candidate = Path(match.strip())
                bases = [ref.parent, *ref.parent.parents, root] if not candidate.is_absolute() else [Path("/")]
                for base in bases:
                    try:
                        resolved = (candidate if candidate.is_absolute() else base / candidate).resolve()
                    except OSError:
                        continue
                    if under(root, resolved):
                        found.add(resolved)
    return found


def plan(manifest: dict, min_age_hours: float = 24.0) -> tuple[dict, Path, Path | None]:
    root_value = manifest.get("project_root")
    if not isinstance(root_value, str) or not Path(root_value).is_absolute():
        raise ValueError("project_root must be an absolute path")
    root = Path(root_value).resolve()
    if not root.is_dir():
        raise ValueError("project_root does not exist")
    generated = [resolve(root, value) for value in manifest.get("generated_roots", [])]
    if not generated or any(path == root or not path.is_dir() or not under(root, path) for path in generated):
        raise ValueError("generated_roots must be existing candidate subdirectories inside project_root")
    references = [resolve(root, value) for value in manifest.get("reference_files", [])]
    if not references:
        raise ValueError("reference_files must name the current EDL/registry/QC files used for reference checks")
    if any(not path.is_file() or not under(root, path) for path in references):
        raise ValueError("every reference_files entry must be a readable file inside project_root")
    referenced = media_references(references, root)

    retained = {}
    retained_paths = set()
    for entry in manifest.get("retained", []):
        path = resolve(root, entry["path"])
        if not path.is_file():
            raise ValueError(f"retained file is missing: {path}")
        retained_paths.add(path)
        if entry.get("shot_id"):
            retained.setdefault(str(entry["shot_id"]), []).append(path)

    archive_value = manifest.get("archive_dir")
    archive = resolve(root, archive_value) if archive_value else None
    if archive and any(under(path, archive) for path in generated):
        raise ValueError("archive_dir must be outside generated_roots")

    now = datetime.now(timezone.utc).timestamp()
    actions = []
    seen = set()
    for item in manifest.get("items", []):
        path = resolve(root, str(item.get("path", "")))
        action = {"path": str(path), "status": "planned",
                  "reason": item.get("reason", ""), "evidence": item.get("evidence", "")}
        actions.append(action)
        if path in seen:
            action.update(status="blocked", code="DUPLICATE_ITEM")
            continue
        seen.add(path)
        if item.get("status") not in ELIGIBLE:
            action.update(status="blocked", code="STATUS_NOT_ELIGIBLE")
            continue
        if not item.get("reason") or not item.get("evidence"):
            action.update(status="blocked", code="REVIEW_EVIDENCE_MISSING")
            continue
        if not any(under(g, path) for g in generated) or not under(root, path):
            action.update(status="blocked", code="OUTSIDE_GENERATED_ROOTS")
            continue
        if not path.exists():
            action.update(status="missing", code="FILE_MISSING")
            continue
        if not path.is_file() or path.is_symlink():
            action.update(status="blocked", code="NOT_A_REGULAR_FILE")
            continue
        if path in referenced:
            action.update(status="blocked", code="STILL_REFERENCED")
            continue
        if path in retained_paths:
            action.update(status="blocked", code="RETAINED_FALLBACK")
            continue
        shot_id = str(item.get("shot_id") or "")
        if shot_id and shot_id not in retained and not item.get("orphan_allowed"):
            action.update(status="blocked", code="NO_RETAINED_FALLBACK")
            continue
        age_hours = (now - path.stat().st_mtime) / 3600
        if age_hours < min_age_hours:
            action.update(status="blocked", code="TOO_RECENT", age_hours=round(age_hours, 3))
            continue
        expected = str(item.get("sha256") or "").lower()
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            action.update(status="blocked", code="SHA256_REQUIRED")
            continue
        actual = digest(path)
        if actual != expected:
            action.update(status="blocked", code="FILE_CHANGED_SINCE_REVIEW",
                          expected_sha256=expected, actual_sha256=actual)
            continue
        action["bytes"] = path.stat().st_size
        action["sha256"] = actual
    result = {
        "project_root": str(root),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "min_age_hours": min_age_hours,
        "actions": actions,
        "summary": {
            "planned": sum(a["status"] == "planned" for a in actions),
            "blocked": sum(a["status"] == "blocked" for a in actions),
            "missing": sum(a["status"] == "missing" for a in actions),
            "bytes_reclaimable": sum(a.get("bytes", 0) for a in actions if a["status"] == "planned"),
        },
    }
    return result, root, archive


def execute(report: dict, root: Path, archive: Path | None, mode: str) -> None:
    if report["summary"]["blocked"]:
        raise ValueError("resolve every blocked item before execution; no media was changed")
    for action in report["actions"]:
        if action["status"] != "planned":
            continue
        source = Path(action["path"])
        if mode == "delete":
            source.unlink()
            action["status"] = "deleted"
        else:
            if archive is None:
                raise ValueError("archive mode requires archive_dir in the manifest")
            target = archive / source.relative_to(root)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                raise FileExistsError(f"archive target already exists: {target}")
            shutil.move(str(source), str(target))
            action.update(status="archived", archived_to=str(target))


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                     prefix=path.name + ".", delete=False) as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp = Path(handle.name)
    os.replace(temp, path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=("archive", "delete"), default="archive")
    parser.add_argument("--execute", action="store_true", help="act; without this flag only dry-run")
    parser.add_argument("--yes", action="store_true", help="explicit confirmation required for --mode delete --execute")
    parser.add_argument("--min-age-hours", type=float, default=24.0)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        report, root, archive = plan(manifest, args.min_age_hours)
        report.update(mode=args.mode, execute=bool(args.execute))
        if args.execute and args.mode == "delete" and not args.yes:
            raise ValueError("deletion requires both --execute and --yes")
        if args.execute:
            execute(report, root, archive, args.mode)
        report["summary"]["completed"] = sum(
            a["status"] in {"deleted", "archived"} for a in report["actions"])
        text = json.dumps(report, ensure_ascii=False, indent=2)
        print(text)
        if args.report:
            atomic_json(args.report, report)
        return 1 if report["summary"]["blocked"] else 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
