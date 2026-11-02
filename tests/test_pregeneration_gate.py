from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "quality_gate_check", ROOT / "skills/produce-ai-video/scripts/quality_gate_check.py")
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def fixture():
    cases = [{"case_id": cid, "split": split, "negative_control": control}
             for cid, split, control in (("dev", "development", False),
                                        ("hold", "holdout", False), ("control", "development", True))]
    reports = []
    for case in cases:
        for i in range(2):
            delta = 0 if case["negative_control"] else 0.1
            reports.append({"case_id": case["case_id"], "replicate_id": str(i),
                            "generation_ids": [f'{case["case_id"]}/{i}/{side}' for side in ("A", "B")],
                            "candidate_label": "B", "preference": "tie" if delta == 0 else "B",
                            "scores": {"A": dict.fromkeys(gate.WEIGHTS, 3),
                                       "B": dict.fromkeys(gate.WEIGHTS, 3 + delta)},
                            "evidence": {"A": "review A", "B": "review B"}})
    return {"cases": cases, "reports": reports}


class PregenerationGateTests(unittest.TestCase):
    def test_weights_and_valid_results_do_not_claim_media_approval(self):
        self.assertEqual(sum(gate.WEIGHTS.values()), 100)
        report = gate.audit(fixture())
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertEqual(report["media_review"], "not_performed")
        self.assertFalse(report["blindness_verified"])

    def test_missing_holdout_control_replicates_and_reused_generation_block(self):
        for mutation in ("holdout", "control", "replicate", "generation"):
            data = fixture()
            if mutation in ("holdout", "control"):
                cid = "hold" if mutation == "holdout" else "control"
                data["cases"] = [c for c in data["cases"] if c["case_id"] != cid]
            elif mutation == "replicate":
                data["reports"].pop()
            else:
                data["reports"][1]["generation_ids"] = data["reports"][0]["generation_ids"]
            with self.subTest(mutation=mutation):
                self.assertEqual(gate.audit(data)["status"], "BLOCK")

    def test_preference_invalid_scores_and_large_control_difference_block(self):
        for mutation in ("preference", "nan", "range", "control"):
            data = fixture()
            row = data["reports"][-1] if mutation == "control" else data["reports"][0]
            if mutation == "preference":
                row["preference"] = "A"
            else:
                row["scores"]["B"] = dict.fromkeys(
                    gate.WEIGHTS, {"nan": float("nan"), "range": 6, "control": 5}[mutation])
            with self.subTest(mutation=mutation):
                self.assertEqual(gate.audit(data)["status"], "BLOCK")

    def test_small_control_win_is_not_automatically_bias(self):
        data = fixture()
        for row in data["reports"]:
            if row["case_id"] == "control":
                row["scores"]["B"] = dict.fromkeys(gate.WEIGHTS, 3.05)
                row["preference"] = "B"
        self.assertNotIn("CONTROL_INVALID", {f["code"] for f in gate.audit(data)["findings"]})

    def test_no_benefit_and_dimension_regression_block(self):
        data = fixture()
        for row in data["reports"]:
            row["scores"]["B"] = copy.deepcopy(row["scores"]["A"])
            row["preference"] = "tie"
        self.assertIn("DEVELOPMENT_NO_BENEFIT", {f["code"] for f in gate.audit(data)["findings"]})
        for row in data["reports"][:2]:
            row["scores"]["B"]["identity_consistency"] = 1
            row["preference"] = "A"
        self.assertIn("DIMENSION_REGRESSION", {f["code"] for f in gate.audit(data)["findings"]})
