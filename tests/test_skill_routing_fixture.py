"""Routing fixture coverage: every Skill has an authored request case."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import skill_routing_eval as routing  # noqa: E402


class SkillRoutingFixtureTests(unittest.TestCase):
    def test_cases_cover_every_skill_and_target_real_names(self):
        cases = json.loads((ROOT / "tests" / "fixtures" / "skill_routing_cases.json")
                           .read_text(encoding="utf-8"))
        skills = set(routing.load_skills())
        self.assertTrue(cases)
        queries = set()
        expected = set()
        for case in cases:
            self.assertIn("query", case)
            self.assertIn("expect", case)
            self.assertIn(case["expect"], skills, f"unknown skill {case['expect']}")
            self.assertNotIn(case["query"], queries, "duplicate routing query")
            queries.add(case["query"])
            expected.add(case["expect"])
        missing = sorted(skills - expected)
        self.assertEqual(missing, [], f"no routing case for: {missing}")


if __name__ == "__main__":
    unittest.main()
