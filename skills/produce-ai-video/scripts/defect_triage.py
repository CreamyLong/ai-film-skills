#!/usr/bin/env python3
"""Aggregate review findings into asset-level repair proposals.

Repeated shot-level defects usually share one asset root cause (one costume
logo, one scene image, one prop policy). This tool clusters findings by
(defect, asset anchor) across episodes and proposes an asset-level task when a
cluster reaches the threshold. Clusters stay ``proposed`` — a human confirms
before any asset rerender is queued.

Exit codes: 0 no proposal, 1 proposals written, 3 error.
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path
import re
import sys

from repair_router import classify

# anchor -> (compiled patterns). Order matters: first match wins.
ANCHORS = [
    ("asset:delivery_uniform", re.compile(r"jacket|delivery|外卖|工装|uniform|背包|backpack", re.I)),
    ("asset:prop_document", re.compile(r"folder|file|document|label|cover|封面|文件|卷宗|档案|登记表|图纸|ledger|envelope", re.I)),
    ("asset:door_signage", re.compile(r"door.*(number|plate|sign)|门牌|门.*号|signage", re.I)),
    ("asset:prop_watch", re.compile(r"watch|表盘|手表", re.I)),
    ("asset:scene_safehouse", re.compile(r"safehouse|s24|安全屋|出租屋|老屋|apartment 103", re.I)),
    ("asset:scene_office", re.compile(r"office|办公室|fluorescent|吊顶", re.I)),
    ("asset:scene_court", re.compile(r"court|法庭|courtroom", re.I)),
    ("asset:character_shenyuan", re.compile(r"shenyuan|沈远|the (son|courier|young)|儿子|外卖员", re.I)),
    ("asset:character_shenguodong", re.compile(r"shenguodong|沈国栋|the (father|old man)|父亲|老者", re.I)),
    ("asset:character_hanzheng", re.compile(r"han ?zheng|韩[正峥]|detective|侦探", re.I)),
    ("asset:character_zhouqiming", re.compile(r"zhou ?qiming|周启明", re.I)),
]

ACTIONS = {
    "asset:delivery_uniform": "regenerate the delivery uniform hero/face without any printed logo, or patch the logo in the asset; then rerender affected shots once",
    "asset:prop_document": "adopt the document policy: closed/face-down/out-of-focus, readable info via clean still inserts; do not rerender for text alone",
    "asset:door_signage": "replace door plates with plain metal or fix one number plate asset; avoid model-generated numbers",
    "asset:prop_watch": "regenerate the watch prop without a dial brand",
    "asset:scene_safehouse": "lock the safehouse set pieces (table, chairs, TV, door, lamp) in one scene asset and rebind every shot in the scene",
    "asset:scene_office": "generate one office scene asset and rebind shots that drifted to invented offices",
    "asset:scene_court": "generate a courtroom scene asset; current courtroom shots are invented",
    "asset:character_shenyuan": "re-audit Shen Yuan's four-image asset pack; regenerate any plate with drift",
    "asset:character_shenguodong": "re-audit Shen Guodong's four-image asset pack; regenerate any plate with drift",
    "asset:character_hanzheng": "re-audit Han Zheng's asset pack and add an identity-establishing insert",
    "asset:character_zhouqiming": "re-audit Zhou Qiming's asset pack",
    "asset:character_pack_general": "audit every character's four-image pack; regenerate plates with drift, then rerun affected shots once",
    "storyboard:dialogue_split": "apply the one-speaker-per-shot policy across the series; split the listed exchanges",
    "generation:artifact_misc": "rerender at 8 steps with new seeds; replace impossible props with stills",
    "asset:text_policy_general": "enforce the document policy series-wide: closed/face-down/out-of-focus plus clean still inserts",
    "asset:scene_general": "audit scene assets per location and rebind shots that drifted",
}


FALLBACK_ANCHORS = {
    "reference_lock": "asset:character_pack_general",
    "speaker_split": "storyboard:dialogue_split",
    "artifact": "generation:artifact_misc",
    "text_prop": "asset:text_policy_general",
    "environment_anchor": "asset:scene_general",
}


def anchor_of(text: str, defect: str | None = None) -> str:
    for name, pattern in ANCHORS:
        if pattern.search(text):
            return name
    return FALLBACK_ANCHORS.get(defect or "", "asset:unknown")


def collect(reports: list[Path]) -> list[dict]:
    findings = []
    for path in reports:
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        episode_match = re.search(r"(EP\d+)", path.name, re.I)
        episode = episode_match.group(1).upper() if episode_match else path.parent.name
        for issue in report.get("issues", []):
            if str(issue.get("severity", "")).lower() not in {"block", "major"}:
                continue
            text = f"{issue.get('claim', '')} {issue.get('evidence', '')}"
            rule = classify(text)
            defect = rule[0] if rule else "unknown_defect"
            findings.append({"episode": episode, "defect": defect,
                             "anchor": anchor_of(text, defect), "time": issue.get("time"),
                             "claim": issue.get("claim")})
    return findings


def triage(reports: list[Path], threshold: int) -> list[dict]:
    findings = collect(reports)
    clusters: dict[tuple, dict] = {}
    for item in findings:
        key = (item["defect"], item["anchor"])
        cluster = clusters.setdefault(key, {"defect": item["defect"], "anchor": item["anchor"],
                                            "episodes": set(), "count": 0, "examples": []})
        cluster["episodes"].add(item["episode"])
        cluster["count"] += 1
        if len(cluster["examples"]) < 3:
            cluster["examples"].append({"episode": item["episode"], "time": item["time"],
                                        "claim": item["claim"]})
    proposals = []
    for cluster in clusters.values():
        if cluster["count"] < threshold or len(cluster["episodes"]) < 2:
            continue
        proposals.append({
            "asset": cluster["anchor"], "defect": cluster["defect"],
            "count": cluster["count"], "episodes": sorted(cluster["episodes"]),
            "action": ACTIONS.get(cluster["anchor"],
                                  "regenerate or rebind the referenced asset, then rerun affected shots"),
            "status": "proposed",
        })
    proposals.sort(key=lambda p: (-p["count"], p["asset"]))
    return proposals


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", required=True,
                        help="glob, e.g. '制作/EP*/EP*_final_omni_review.json'")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--threshold", type=int, default=3)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    reports = [Path(p) for p in sorted(glob.glob(args.reports))]
    if not reports:
        print(json.dumps({"status": "error", "error": "no reports matched"}, ensure_ascii=False))
        return 3
    proposals = triage(reports, args.threshold)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"status": "proposed" if proposals else "clean",
                                    "threshold": args.threshold, "reports": len(reports),
                                    "proposals": proposals}, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    result = {"status": "proposed" if proposals else "clean", "proposals": len(proposals),
              "out": str(args.out)}
    print(json.dumps(result, ensure_ascii=False) if args.json else
          json.dumps(result, ensure_ascii=False, indent=2))
    for proposal in proposals:
        print(f"[{proposal['count']}x/{len(proposal['episodes'])}eps] {proposal['asset']} "
              f"{proposal['defect']}: {proposal['action']}")
    return 1 if proposals else 0


if __name__ == "__main__":
    sys.exit(main())
