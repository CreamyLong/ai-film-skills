#!/usr/bin/env python3
"""Route review findings to the earliest responsible layer and queue repairs.

Reads an auto_review-style report (status + issues) and emits deterministic
repair tasks. It never rewrites a prompt by itself: structural findings are
marked ``authored`` and must be redesigned by the shot-risk policy.

Exit codes: 0 no task, 1 tasks written, 3 error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

# Ordered: the first matching rule owns the finding.
RULES = [
    ("assembly_truncation", r"时长|duration|少.*秒|截短|跳切|concat|拼接",
     "edit", "verify duration against sum of segments; rebuild with concat filter", True),
    ("audio_gain", r"响度|level|dB|爆音|底噪|房间声|声音.*跳|audio.*jump",
     "sound", "apply measured per-shot gain and L-cut, then recheck cut RMS", True),
    ("text_prop", r"text|文字|乱码|伪字|gibberish|label|标题|封面|plate|signage|logo|door number|门牌",
     "prompt/edit", "keep the text prop out of focus/closed, or insert a clean still; do not rerender the same framing", False),
    ("prompt_contract", r"prompt|提示词|台词.*不清|speech.*unclear|dialogue.*unclear|对白.*含糊|missing dialogue|台词缺失",
     "prompt", "run scripts/shot_contract_check.py and prompt_preflight, fix the prompt structure, then rerender", False),
    ("speaker_split", r"speaker|说话人|口型|lip|mouth|对调|attribution|旁白.*口型",
     "storyboard", "split into one shot per speaker; one visible mouth per shot", False),
    ("reference_lock", r"wardrobe|服装|衬衫|shirt|jacket|衣服|coat|外套|identity|身份|face|脸|hair|发型|scar|伤疤|换人|换脸|costume",
     "asset/generation", "lock the character references and rerender; same scene shots must share the same wardrobe/scene refs", True),
    ("environment_anchor", r"space|空间|room|房间|location|地点|background|背景|door|门|street|街|office|办公室|teleport",
     "asset/generation", "attach the same environment reference (and video continuity ref) to every shot in the scene", True),
    ("artifact", r"hand|手指|finger|ghost|重影|漂浮|floating|melting|穿模|extra person|多出|artifact|伪影",
     "generation", "rerender at 8 steps with a new seed, or replace the impossible prop with a still", True),
]


def classify(text: str) -> tuple[str, str, str, bool] | None:
    lowered = text.lower()
    for name, pattern, owner, action, auto in RULES:
        if re.search(pattern, lowered, re.I):
            return name, owner, action, auto
    return None


def shot_id(video: str, explicit: str | None) -> str | None:
    if explicit:
        return explicit
    match = re.search(r"shot([A-Za-z0-9]+)", Path(video).stem, re.I)
    return match.group(1) if match else None


def episode_id(video: str | None) -> str | None:
    match = re.search(r"(EP\d+)", Path(video or "").name, re.I)
    return match.group(1).upper() if match else None


def _seconds(value: str) -> float | None:
    match = re.match(r"(?:(\d+):)?(\d+(?:\.\d+)?)$", str(value).strip())
    if not match:
        return None
    return int(match.group(1) or 0) * 60 + float(match.group(2))


def _duration(path: Path) -> float:
    import subprocess
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def time_to_shot(time_value: str | None, editlist: Path | None) -> str | None:
    seconds = _seconds(time_value or "")
    if seconds is None or editlist is None or not editlist.exists():
        return None
    try:
        data = json.loads(editlist.read_text(encoding="utf-8"))
    except ValueError:
        return None
    root = editlist.parent.parent
    cursor = 0.0
    last = None
    for seg in data.get("segments", []):
        if seg.get("still"):
            duration = float(seg.get("duration", 0))
        else:
            source = root / seg["src"]
            duration = _duration(source) if source.exists() else 0.0
        last = seg.get("name")
        if cursor <= seconds < cursor + duration:
            return last
        cursor += duration
    return last


def route(report: dict, video: str | None = None, shot: str | None = None,
          editlist: Path | None = None, episode_dir: Path | None = None,
          use_decision: bool = False) -> list[dict]:
    tasks = []
    video = video or report.get("video")
    for issue in report.get("issues", []):
        severity = str(issue.get("severity", "minor")).lower()
        if severity not in {"block", "major"}:
            continue
        text = f"{issue.get('claim', '')} {issue.get('evidence', '')}"
        rule = classify(text)
        if rule is None and use_decision:
            try:
                from decision_client import triage
                answer = triage(text)
                if (answer.get("defect") and answer["defect"] != "unknown_defect"
                        and (answer.get("confidence") or 0) >= 0.5):
                    defect = answer["defect"]
                    structural = bool(answer.get("structural"))
                    auto = structural
                    owner = "generation" if structural else "storyboard"
                    action = ("rerender at 8 steps with a new seed, then re-review"
                              if structural else
                              "redesign the shot structure; do not reword the same framing")
                else:
                    defect, owner, action, auto = (
                        "unknown_defect", "generation",
                        "rerender at 8 steps with a new seed and re-review; "
                        "escalate only if the same defect repeats", True)
            except Exception:
                defect, owner, action, auto = (
                    "unknown_defect", "generation",
                    "rerender at 8 steps with a new seed and re-review; "
                    "escalate only if the same defect repeats", True)
        elif rule is None:
            defect, owner, action, auto = (
                "unknown_defect", "generation",
                "rerender at 8 steps with a new seed and re-review; "
                "escalate only if the same defect repeats", True)
        else:
            defect, owner, action, auto = rule
        resolved_shot = time_to_shot(issue.get("time"), editlist) or shot_id(video or "", shot)
        task = {
            "episode": episode_id(video),
            "episode_video": video,
            "shot": resolved_shot,
            "time": issue.get("time"),
            "severity": severity,
            "defect": defect,
            "owner": owner,
            "action": action,
            "auto_rerender": auto,
            "mode": "auto" if auto else "authored",
            "claim": issue.get("claim"),
            "evidence": issue.get("evidence"),
            "report": report.get("video"),
            "status": "queued",
        }
        if auto and resolved_shot and episode_dir:
            task["suggested_command"] = (
                f"cd {episode_dir.resolve()} && python3 scripts/<generation-entry>.py "
                f"--shots {resolved_shot} --steps 8 --force --tag _repair")
        tasks.append(task)
    return tasks


def task_key(task: dict) -> str:
    raw = f"{task.get('shot')}|{task.get('defect')}|{task.get('time')}|{task.get('claim')}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def append_queue(tasks: list[dict], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            existing = []
    seen = {t.get("key") for t in existing}
    added = 0
    for task in tasks:
        task["key"] = task_key(task)
        if task["key"] in seen:
            continue
        existing.append(task)
        seen.add(task["key"])
        added += 1
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    return added


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--shot", default=None)
    parser.add_argument("--editlist", type=Path, default=None,
                        help="map issue timestamps to shot ids")
    parser.add_argument("--episode-dir", type=Path, default=None,
                        help="episode package root for suggested commands")
    parser.add_argument("--decision", action="store_true",
                        help="use SystemOne intern-decision-4b for unknown findings")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = json.loads(args.review.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)[:500]}, ensure_ascii=False))
        return 3
    tasks = route(report, shot=args.shot, editlist=args.editlist,
                  episode_dir=args.episode_dir, use_decision=args.decision)
    added = append_queue(tasks, args.queue)
    result = {"status": "queued" if tasks else "clean", "tasks": tasks, "added": added,
              "queue": str(args.queue)}
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(json.dumps({"status": result["status"], "added": added,
                          "queue": str(args.queue)}, ensure_ascii=False))
        for task in tasks:
            print(f"[{task['mode']}] {task['severity']} {task['shot']} "
                  f"{task['defect']}: {task['action']}")
    return 1 if tasks else 0


if __name__ == "__main__":
    sys.exit(main())
