"""Repair close-the-loop and cross-episode defect triage."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


SCRIPTS = ROOT / "skills" / "produce-ai-video" / "scripts"
sys_path_added = str(SCRIPTS)
if sys_path_added not in __import__("sys").path:
    __import__("sys").path.insert(0, sys_path_added)


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


close = load("repair_close")
triage = load("defect_triage")


class RepairCloseTests(unittest.TestCase):
    def test_defect_gone_closes_task(self):
        report = {"issues": [{"severity": "minor", "claim": "logo small"}]}
        self.assertNotIn("reference_lock", close.defects_of(report))

    def test_still_major_escalates(self):
        report = {"issues": [{"severity": "major", "claim": "shirt changes color"}]}
        self.assertEqual(close.defects_of(report).get("reference_lock"), "major")

    def test_close_tasks_updates_queue(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            queue = root / "queue.json"
            queue.write_text(json.dumps([
                {"status": "queued", "shot": "07", "defect": "reference_lock"}]))
            reviews = root / "reviews"
            reviews.mkdir()
            (reviews / "shot07_omni_review.json").write_text(
                json.dumps({"issues": [{"severity": "minor", "claim": "logo small"}]}))
            summary = close.close_tasks(queue, reviews)
            self.assertEqual(summary["closed"], 1)
            self.assertEqual(json.loads(queue.read_text())[0]["status"], "closed")


class PromptRiskScanTests(unittest.TestCase):
    def test_flags_high_risk_and_passes_clean(self):
        import sys, tempfile, json
        scanner = load("prompt_risk_scan")
        def fake_decide(state, questions, timeout=60):
            return {k: {"type": "noul", "noul": 0.9} for k in questions}
        sys.modules["decision_client"] = type("M", (), {"decide": staticmethod(fake_decide)})()
        try:
            with tempfile.TemporaryDirectory() as raw:
                path = Path(raw) / "p.json"
                path.write_text(json.dumps({"shots": [
                    {"shot": "01", "prompt": "summary:
detailed_description:
[Shot 1] A speaks."},
                    {"shot": "02", "prompt": "summary:
detailed_description:
[Shot 1] B walks."},
                ]}))
                report = scanner.scan_prompts(path, None)
        finally:
            sys.modules.pop("decision_client", None)
        self.assertEqual(report["status"], "block")
        self.assertEqual(len(report["findings"]), 6)


class DefectTriageTests(unittest.TestCase):
    def test_repeated_anchor_becomes_proposal(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for ep in ("EP001", "EP002", "EP003"):
                (root / f"{ep}_final_omni_review.json").write_text(json.dumps({
                    "issues": [{"severity": "major", "time": "00:01",
                                "claim": "delivery jacket logo garbled"}]}))
            reports = sorted(root.glob("*.json"))
            proposals = triage.triage(reports, threshold=3)
            self.assertEqual(len(proposals), 1)
            self.assertEqual(proposals[0]["asset"], "asset:delivery_uniform")
            self.assertEqual(proposals[0]["count"], 3)

    def test_decision_gate_demotes_low_confidence(self):
        import sys
        def fake_decide(state, questions, timeout=60):
            return {"same_root_cause": {"type": "noul", "noul": 0.2}}
        fake_module = type("M", (), {"decide": staticmethod(fake_decide)})()
        sys.modules["decision_client"] = fake_module
        try:
            kept = triage.decision_gate([
                {"asset": "a", "defect": "b", "examples": [], "status": "proposed"},
                {"asset": "c", "defect": "d", "examples": [], "status": "proposed"},
            ])
        finally:
            sys.modules.pop("decision_client", None)
        self.assertEqual(len(kept), 0)

    def test_below_threshold_stays_clean(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for ep in ("EP001", "EP002"):
                (root / f"{ep}_final_omni_review.json").write_text(json.dumps({
                    "issues": [{"severity": "major", "claim": "watch dial garbled"}]}))
            self.assertEqual(triage.triage(sorted(root.glob("*.json")), threshold=3), [])


if __name__ == "__main__":
    unittest.main()
