"""The auto-review verdict parser must fail closed to review."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "produce-ai-video" / "scripts" / "auto_review.py"
SPEC = importlib.util.spec_from_file_location("auto_review", SCRIPT)
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


class AutoReviewParserTests(unittest.TestCase):
    def test_parses_fenced_json(self):
        verdict = gate.parse_verdict('```json\n{"status":"block","issues":[]}\n```')
        self.assertEqual(verdict["status"], "block")

    def test_unknown_status_is_unusable(self):
        self.assertIsNone(gate.parse_verdict('{"status":"maybe"}'))
        self.assertIsNone(gate.parse_verdict("no json here"))

    def test_missing_issues_defaults_at_call_site(self):
        verdict = gate.parse_verdict('{"status":"pass"}')
        self.assertEqual(verdict["status"], "pass")
        self.assertEqual(verdict.get("issues", []), [])


if __name__ == "__main__":
    unittest.main()
