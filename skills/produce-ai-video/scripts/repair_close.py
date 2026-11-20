#!/usr/bin/env python3
"""Close the repair loop: re-check queued tasks against fresh review reports.

For each queued task with a shot id, locate the newest auto_review report for
that shot (or the episode final report when no shot is mapped) and compare the
defect list. A task is closed only when its defect no longer appears; a task
whose defect still shows as major/block is escalated; a downgrade to minor is
recorded as reduced and stays open.

Exit codes: 0 nothing changed, 1 queue updated, 3 error.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from repair_router import classify


def defects_of(report: dict) -> dict[str, str]:
    """Return {defect: highest severity} for one auto_review-style report."""
    result: dict[str, str] = {}
    rank = {"block": 3, "major": 2, "review": 1, "minor": 0}
    for issue in report.get("issues", []):
        severity = str(issue.get("severity", "minor")).lower()
        rule = classify(f"{issue.get('claim', '')} {issue.get('evidence', '')}")
        defect = rule[0] if rule else "unknown_defect"
        if defect not in result or rank.get(severity, 0) > rank.get(result[defect], 0):
            result[defect] = severity
    return result


def newest_report(task: dict, review_root: Path, episode_dir: Path | None) -> Path | None:
    shot = task.get("shot")
    candidates = []
    if shot and review_root.exists():
        candidates = sorted(review_root.glob(f"shot{shot}*_omni_review.json"),
                            key=lambda p: p.stat().st_mtime)
    if not candidates and episode_dir is not None:
        episode = task.get("episode") or (episode_dir.name if episode_dir else "")
        if episode:
            candidates = sorted(episode_dir.glob(f"{episode}_final_omni_review.json"))
    return candidates[-1] if candidates else None


def close_tasks(queue_path: Path, review_root: Path | None,
                episode_dir: Path | None = None) -> dict:
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    summary = Counter()
    for task in queue:
        if task.get("status") not in {"queued", "escalated"}:
            continue
        report_path = newest_report(task, review_root or Path("/nonexistent"), episode_dir)
        if report_path is None:
            summary["no_report"] += 1
            continue
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except ValueError:
            summary["bad_report"] += 1
            continue
        defects = defects_of(report)
        defect = task.get("defect")
        current = defects.get(defect)
        task["last_report"] = str(report_path)
        if current is None:
            task["status"] = "closed"
            task["close_note"] = f"{defect} no longer appears in {report_path.name}"
            summary["closed"] += 1
        elif current in {"block", "major"}:
            task["status"] = "escalated"
            task["close_note"] = f"{defect} still {current} in {report_path.name}"
            summary["escalated"] += 1
        else:
            task["status"] = "reduced"
            task["close_note"] = f"{defect} downgraded to {current} in {report_path.name}"
            summary["reduced"] += 1
    queue_path.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    return dict(summary)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", required=True, type=Path)
    parser.add_argument("--review-root", type=Path, default=None,
                        help="directory holding shot*_omni_review.json files")
    parser.add_argument("--episode-dir", type=Path, default=None,
                        help="fallback directory holding EP*_final_omni_review.json")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.queue.exists():
        print(json.dumps({"status": "error", "error": "missing queue"}, ensure_ascii=False))
        return 3
    summary = close_tasks(args.queue, args.review_root, args.episode_dir)
    result = {"status": "updated" if any(v for v in summary.values()) else "no_change",
              "summary": summary, "queue": str(args.queue)}
    print(json.dumps(result, ensure_ascii=False) if args.json else
          json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "updated" else 0


if __name__ == "__main__":
    sys.exit(main())
