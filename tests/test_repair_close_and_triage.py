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

    def test_below_threshold_stays_clean(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for ep in ("EP001", "EP002"):
                (root / f"{ep}_final_omni_review.json").write_text(json.dumps({
                    "issues": [{"severity": "major", "claim": "watch dial garbled"}]}))
            self.assertEqual(triage.triage(sorted(root.glob("*.json")), threshold=3), [])


if __name__ == "__main__":
    unittest.main()
