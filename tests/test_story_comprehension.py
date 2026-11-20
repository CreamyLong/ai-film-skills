"""Story comprehension parser and verdict thresholds."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "story_comprehension_review",
    ROOT / "skills" / "omni-review" / "scripts" / "story_comprehension_review.py")
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def answer(clarity=8, appeal=8, confusions=None):
    return {"setting": "A", "goals": "B", "events": [], "turn": "C",
            "cliffhanger": "D", "confusions": confusions or [],
            "clarity": clarity, "appeal": appeal}


class StoryComprehensionTests(unittest.TestCase):
    def test_parse_fenced_json(self):
        parsed = gate.parse_answer('```json\n{"clarity": 7, "appeal": 6}\n```')
        self.assertEqual(parsed["clarity"], 7)

    def test_parse_rejects_prose(self):
        self.assertIsNone(gate.parse_answer("just prose"))

    def test_clean_answer_passes(self):
        status, _ = gate.verdict(answer())
        self.assertEqual(status, "pass")

    def test_low_clarity_is_review(self):
        status, reasons = gate.verdict(answer(clarity=5))
        self.assertEqual(status, "review")
        self.assertTrue(any("clarity" in r for r in reasons))

    def test_many_confusions_block(self):
        status, _ = gate.verdict(answer(confusions=["a", "b", "c"]))
        self.assertEqual(status, "block")

    def test_one_confusion_is_review(self):
        status, _ = gate.verdict(answer(confusions=["who is he?"]))
        self.assertEqual(status, "review")


if __name__ == "__main__":
    unittest.main()
