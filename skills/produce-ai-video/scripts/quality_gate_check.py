from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


WEIGHTS = {
    "identity_consistency": 20, "motion_continuity": 15, "action_legibility": 15,
    "prompt_fidelity": 15, "camera_and_composition": 10, "audio_quality": 10,
    "cut_continuity": 10, "story_readability": 5,
}


def audit(record):
    findings = []

    def add(code, location):
        findings.append({"code": code, "location": location, "severity": "block"})

    cases = {}
    for case in record.get("cases", []):
        cid = case.get("case_id")
        if (not isinstance(cid, str) or not cid.strip() or cid in cases
                or case.get("split") not in ("development", "holdout")
                or type(case.get("negative_control")) is not bool):
            add("CASE_INVALID", str(cid))
        else:
            cases[cid] = case
    if not any(c["negative_control"] for c in cases.values()):
        add("CONTROL_MISSING", "/cases")
    for split in ("development", "holdout"):
        if not any(c["split"] == split and not c["negative_control"] for c in cases.values()):
            add("SPLIT_MISSING", split)
    groups = {cid: [] for cid in cases}
    seen = set()
    generations = set()
    for report in record.get("reports", []):
        cid, rid = report.get("case_id"), report.get("replicate_id")
        loc = f"{cid}/{rid}"
        if cid not in cases or not isinstance(rid, str) or not rid or (cid, rid) in seen:
            add("REPORT_ID_INVALID", loc)
            continue
        seen.add((cid, rid))
        ids = report.get("generation_ids")
        if (not isinstance(ids, list) or len(ids) != 2
                or any(not isinstance(gid, str) or not gid for gid in ids)
                or len(set(ids)) != 2 or any(gid in generations for gid in ids)):
            add("GENERATION_REUSED_OR_MISSING", loc)
            continue
        generations.update(ids)
        scores = report.get("scores", {})
        evidence = report.get("evidence", {})
        valid = True
        for label in ("A", "B"):
            values = scores.get(label, {})
            if (not isinstance(values, dict) or set(values) != set(WEIGHTS)
                    or any(type(v) not in (int, float) or not math.isfinite(v)
                           or not 0 <= v <= 5 for v in values.values())
                    or not isinstance(evidence.get(label), str) or not evidence[label].strip()):
                valid = False
        candidate = report.get("candidate_label")
        if not valid or candidate not in ("A", "B"):
            add("SCORES_OR_EVIDENCE_INVALID", loc)
            continue
        totals = {label: sum(scores[label][key] * weight / 5 for key, weight in WEIGHTS.items())
                  for label in ("A", "B")}
        preference = "tie" if abs(totals["A"] - totals["B"]) <= 0.5 \
            else max(totals, key=totals.get)
        if report.get("preference") != preference:
            add("PREFERENCE_CONTRADICTS_SCORES", loc)
        baseline = "B" if candidate == "A" else "A"
        groups[cid].append((totals[candidate] - totals[baseline],
                            {key: scores[candidate][key] - scores[baseline][key]
                             for key in WEIGHTS}))
    means = {}
    for cid, rows in groups.items():
        if len(rows) < 2:
            add("REPLICATES_INSUFFICIENT", cid)
            continue
        delta = sum(row[0] for row in rows) / len(rows)
        means[cid] = delta
        if cases[cid]["negative_control"]:
            if abs(delta) > 2:
                add("CONTROL_INVALID", cid)
        elif delta < -2:
            add("CASE_REGRESSION", cid)
        if any(sum(row[1][key] for row in rows) / len(rows) < -1 for key in WEIGHTS):
            add("DIMENSION_REGRESSION", cid)
    development = [means[cid] for cid, case in cases.items()
                   if cid in means and case["split"] == "development" and not case["negative_control"]]
    if development and sum(development) / len(development) < 1:
        add("DEVELOPMENT_NO_BENEFIT", "/cases")
    return {"status": "BLOCK" if findings else "REVIEW_REQUIRED", "findings": findings,
            "mean_delta": means, "media_review": "not_performed",
            "authorization_review": "not_performed", "blindness_verified": False}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = audit(json.loads(args.input.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print(json.dumps({"status": "INVALID_INPUT", "error": str(exc)}))
        return 1
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 1 if result["status"] == "BLOCK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
