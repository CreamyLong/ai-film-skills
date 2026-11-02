from __future__ import annotations

import importlib.util
import copy
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "series_check", ROOT / "skills/ai-short-drama-production/scripts/series_check.py")
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def bible(**kw):
    base = {
        "series_id": "s01",
        "title": "demo",
        "entities": [
            {"id": "C01", "kind": "character", "name": "Lin", "appearance": "short black hair, grey suit", "locked": True},
            {"id": "S01", "kind": "location", "name": "office"},
            {"id": "P01", "kind": "prop", "name": "ring"},
        ],
        "threads": [{"id": "T1", "opened_in": 1, "closed_in": None, "summary": "missing ring"}],
        "initial_state": [{"entity": "C01", "key": "status", "value": "healthy"}],
        "episodes": [],
    }
    base.update(kw)
    return base


def outline(no=1, **kw):
    base = {
        "episode_no": no,
        "title": f"ep{no}",
        "premise": "Lin hunts the ring.",
        "hook": "The ring is gone.",
        "want": "Lin wants the ring back.",
        "obstacle": "The suspect denies it.",
        "strategy_shift": "Lin bluffs.",
        "power_turn": "The suspect slips.",
        "cost": "Lin reveals her source.",
        "cliffhanger": "A second ring appears.",
        "entry_state": [{"entity": "C01", "key": "status", "value": "healthy"}],
        "exit_state": [{"entity": "C01", "key": "status", "value": "injured"}],
        "entities_used": ["C01", "S01", "P01"],
        "entity_deltas": {"introduces": [], "departs": []},
        "threads": {"opens": [], "closes": []},
    }
    base.update(kw)
    return base


def codes(report):
    return {item["code"] for item in report["findings"]}


class SeriesCheckTest(unittest.TestCase):
    def test_clean_series_passes(self):
        report = checker.audit(bible(), [outline(), outline(
            2, entry_state=[{"entity": "C01", "key": "status", "value": "injured"}])])
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["episodes_checked"], 2)

    def test_entry_state_mismatch_blocks(self):
        report = checker.audit(bible(), [outline(), outline(2)])
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("SERIES_ENTRY_STATE_MISMATCH", codes(report))

    def test_unregistered_entity_blocks(self):
        report = checker.audit(bible(), [outline(entities_used=["C01", "C09"])])
        self.assertIn("SERIES_ENTITY_UNREGISTERED", codes(report))

    def test_introduced_entity_is_accepted_but_flagged(self):
        deltas = {"introduces": [{"id": "C09", "kind": "character", "name": "new"}], "departs": []}
        report = checker.audit(bible(), [outline(entities_used=["C01", "C09"], entity_deltas=deltas)])
        self.assertNotIn("SERIES_ENTITY_UNREGISTERED", codes(report))
        self.assertIn("SERIES_INTRODUCTION_UNREGISTERED", codes(report))

    def test_departed_entity_reuse_blocks(self):
        ep1 = outline(entity_deltas={"introduces": [], "departs": ["P01"]})
        ep2 = outline(2, entry_state=[{"entity": "C01", "key": "status", "value": "injured"},
                                      {"entity": "P01", "key": "location", "value": "vault"}])
        report = checker.audit(bible(), [ep1, ep2])
        self.assertIn("SERIES_DEPARTED_USED", codes(report))

    def test_locked_appearance_change_blocks(self):
        entry = [{"entity": "C01", "key": "appearance", "value": "long red hair"}]
        report = checker.audit(bible(), [outline(entry_state=entry)])
        self.assertIn("SERIES_LOCKED_APPEARANCE_CHANGE", codes(report))

    def test_thread_close_unopened_blocks(self):
        report = checker.audit(bible(), [outline(threads={"opens": [], "closes": ["T9"]})])
        self.assertIn("SERIES_THREAD_CLOSE_UNOPENED", codes(report))

    def test_open_then_close_is_fine(self):
        threads = {"opens": [{"id": "T2", "summary": "second ring"}], "closes": ["T1"]}
        report = checker.audit(bible(), [outline(threads=threads)])
        self.assertNotIn("SERIES_THREAD_CLOSE_UNOPENED", codes(report))
        self.assertNotIn("SERIES_THREAD_REOPEN", codes(report))

    def test_bible_schema_findings(self):
        bad = bible(entities=[{"id": "C01", "kind": "character", "locked": True},
                              {"id": "C01", "kind": "ghost"},
                              {"id": "S02"}])
        report = checker.audit(bad, [])
        self.assertIn("SERIES_DUPLICATE_ENTITY", codes(report))
        self.assertIn("SERIES_ENTITY_KIND", codes(report))
        self.assertIn("SERIES_LOCKED_NO_APPEARANCE", codes(report))

    def test_incomplete_outline_blocks(self):
        bad = outline(hook="", cliffhanger="")
        del bad["premise"]
        report = checker.audit(bible(), [bad])
        found = [f for f in report["findings"] if f["code"] == "EPISODE_OUTLINE_INCOMPLETE"]
        self.assertGreaterEqual(len(found), 3)

    def test_episode_gap_is_review(self):
        report = checker.audit(bible(), [outline(1), outline(
            3, entry_state=[{"entity": "C01", "key": "status", "value": "injured"}])])
        self.assertIn("SERIES_EPISODE_GAP", codes(report))

    def test_incremental_check_replays_history_without_mutating_inputs(self):
        saved = bible(episodes=[outline()])
        before = copy.deepcopy(saved)
        current = outline(2, entry_state=[{"entity": "C01", "key": "status", "value": "injured"}])
        report = checker.audit(saved, [current])
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["history_episodes_replayed"], 1)
        self.assertEqual(len(report["history_sha256"]), 64)
        self.assertEqual(saved, before)

    def test_incremental_reset_to_initial_state_blocks(self):
        report = checker.audit(bible(episodes=[outline()]), [outline(2)])
        self.assertIn("SERIES_ENTRY_STATE_MISMATCH", codes(report))

    def test_changed_history_cannot_be_silently_replaced(self):
        report = checker.audit(bible(episodes=[outline()]), [outline(title="replacement")])
        self.assertIn("SERIES_HISTORY_CONFLICT", codes(report))

    def test_identical_overlap_is_checked_once(self):
        report = checker.audit(bible(episodes=[outline()]), [outline()])
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["episodes_checked"], 1)

    def test_missing_history_and_changed_history_pin_block(self):
        self.assertIn("SERIES_HISTORY_INCOMPLETE", codes(checker.audit(bible(), [outline(2)])))
        report = checker.audit(bible(), [outline()], expected_history_sha256="0" * 64)
        self.assertIn("SERIES_HISTORY_HASH_MISMATCH", codes(report))

    def test_future_thread_cannot_close_or_open_early(self):
        future = [{"id": "T9", "opened_in": 5, "closed_in": None}]
        for threads in ({"opens": [], "closes": ["T9"]},
                        {"opens": [{"id": "T9"}], "closes": []}):
            with self.subTest(threads=threads):
                report = checker.audit(bible(threads=future), [outline(threads=threads)])
                self.assertEqual(report["status"], "BLOCK")

    def test_thread_closed_in_history_is_not_reopened_by_registry(self):
        saved = outline(threads={"opens": [], "closes": ["T1"]})
        current = outline(2, entry_state=[{"entity": "C01", "key": "status", "value": "injured"}],
                          threads={"opens": [], "closes": ["T1"]})
        report = checker.audit(bible(episodes=[saved]), [current])
        self.assertIn("SERIES_THREAD_CLOSE_UNOPENED", codes(report))

    def test_explicit_return_clears_departure(self):
        first = outline(entity_deltas={"introduces": [], "departs": ["P01"]})
        second = outline(2, entry_state=[{"entity": "C01", "key": "status", "value": "injured"}],
                         entity_deltas={"introduces": [], "departs": [], "returns": ["P01"]})
        report = checker.audit(bible(), [first, second])
        self.assertNotIn("SERIES_DEPARTED_USED", codes(report))
        bad = checker.audit(bible(), [outline(entity_deltas={"returns": ["C99"]})])
        self.assertIn("SERIES_RETURN_INVALID", codes(bad))

    def test_resolved_episode_need_not_have_a_cliffhanger(self):
        report = checker.audit(bible(), [outline(cliffhanger="", resolution="The ring is returned.")])
        self.assertNotIn("EPISODE_OUTLINE_INCOMPLETE", codes(report))

    def test_invalid_history_and_thread_dates_are_findings(self):
        self.assertEqual(checker.audit(bible(episodes=["invalid"]), [outline()])["status"], "BLOCK")
        for opened, closed in (("five", 3), (True, None), (1, "later")):
            report = checker.audit(bible(threads=[{"id": "T1", "opened_in": opened,
                                                   "closed_in": closed}]), [outline()])
            self.assertEqual(report["status"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
