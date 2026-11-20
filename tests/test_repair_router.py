"""Review findings must route to the right repair layer and queue idempotently."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("repair_router", ROOT / "skills" / "produce-ai-video" / "scripts" / "repair_router.py")
router = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(router)


def report(*issues):
    return {"status": "review", "video": "video/v1/shot07.mp4", "issues": list(issues)}


def issue(severity, claim, evidence=""):
    return {"severity": severity, "time": "00:01", "claim": claim, "evidence": evidence}


class RepairRouterTests(unittest.TestCase):
    def test_wardrobe_becomes_autor_reference_lock(self):
        tasks = router.route(report(issue("major", "Wardrobe continuity break", "shirt changes")))
        self.assertEqual(tasks[0]["defect"], "reference_lock")
        self.assertTrue(tasks[0]["auto_rerender"])
        self.assertEqual(tasks[0]["shot"], "07")

    def test_text_prop_is_authored_not_rerendered(self):
        tasks = router.route(report(issue("major", "Gibberish text on folder cover", "mirrored glyphs")))
        self.assertEqual(tasks[0]["defect"], "text_prop")
        self.assertFalse(tasks[0]["auto_rerender"])
        self.assertEqual(tasks[0]["mode"], "authored")

    def test_speaker_mismatch_requires_split(self):
        tasks = router.route(report(issue("major", "Speaker attribution reversed", "mouth moves")))
        self.assertEqual(tasks[0]["defect"], "speaker_split")
        self.assertFalse(tasks[0]["auto_rerender"])

    def test_minor_findings_are_ignored(self):
        self.assertEqual(router.route(report(issue("minor", "small logo"))), [])

    def test_unknown_finding_is_auto_not_human(self):
        tasks = router.route(report(issue("block", "something weird")))
        self.assertEqual(tasks[0]["defect"], "unknown_defect")
        self.assertEqual(tasks[0]["mode"], "auto")
        self.assertTrue(tasks[0]["auto_rerender"])

    def test_prompt_wording_is_routed_to_prompt_layer(self):
        tasks = router.route(report(issue("major", "Dialogue unclear", "speech is slurred")))
        self.assertEqual(tasks[0]["defect"], "prompt_contract")
        self.assertEqual(tasks[0]["owner"], "prompt")

    def test_queue_deduplicates(self):
        tasks = router.route(report(issue("major", "Wardrobe continuity break")))
        with tempfile.TemporaryDirectory() as raw:
            queue = Path(raw) / "queue.json"
            self.assertEqual(router.append_queue(tasks, queue), 1)
            again = router.route(report(issue("major", "Wardrobe continuity break")))
            self.assertEqual(router.append_queue(again, queue), 0)
            self.assertEqual(len(json.loads(queue.read_text())), 1)


if __name__ == "__main__":
    unittest.main()
