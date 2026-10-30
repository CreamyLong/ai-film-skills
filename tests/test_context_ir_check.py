from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "context_ir_check", ROOT / "skills/produce-ai-video/scripts/context_ir_check.py")
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)

VALID = """subject_definitions:
<Subject 1> is the examiner in <Picture 1>, wearing a dark coat.
<Picture 1> is the first frame of [Shot 1], showing a meeting room.
<Audio 1> is the voice-timbre reference for <Subject 1> (S1).

summary:
[reference generation + audio reference] <Subject 1> speaks in the meeting room anchored by <Picture 1>.

retention_analysis:
<Subject 1> (appears in [Shot 1], [Shot 2]): fully_preserved - identity and wardrobe are retained.
<Picture 1> ([Shot 1] first frame): fully_preserved - the opening composition is retained.
<Audio 1>: reference - its timbre guides <Subject 1> without copying the signal.

detailed_description:
A quiet meeting room in flat daylight.
[Shot 1] <Subject 1> (S1) turns toward the table and says, <d>[Mandarin] 会议开始。</d>
[Shot 2] At 00:05.000, the camera cuts to <Picture 1> as <Subject 1> (S1) continues off-screen.

overall_soundscape:
Quiet room tone continues throughout.

non_diegetic_music:
N/A
"""


def codes(report):
    return {item["code"] for item in report["findings"]}


class ContextIrCheckTests(unittest.TestCase):
    def test_valid_structure_has_no_findings(self):
        report = checker.audit(VALID, duration_seconds=10)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertEqual(report["semantic_review"], "not_performed")

    def test_missing_section_blocks(self):
        report = checker.audit(VALID.replace("retention_analysis:", "notes:"))
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("SECTION_STRUCTURE", codes(report))

    def test_undefined_body_label_blocks(self):
        report = checker.audit(VALID.replace("<Subject 1> (S1) turns", "<Subject 2> (S1) turns"))
        self.assertIn("BODY_LABEL_UNDEFINED", codes(report))

    def test_wrong_marker_kind_blocks(self):
        report = checker.audit(VALID.replace("<Audio 1>: reference", "<Audio 1>: fully_preserved"))
        self.assertIn("RETENTION_MARKER_INVALID", codes(report))

    def test_retention_for_undefined_label_blocks(self):
        report = checker.audit(VALID.replace("<Audio 1>: reference", "<Audio 9>: reference"))
        self.assertIn("RETENTION_UNDEFINED", codes(report))

    def test_shot_numbering_and_cut_times(self):
        bad = VALID.replace("[Shot 2] At 00:05.000", "[Shot 3] At 00:04.000")
        report = checker.audit(bad, duration_seconds=10)
        self.assertIn("SHOT_NUMBERING", codes(report))
        bad2 = VALID.replace("[Shot 2] At 00:05.000", "[Shot 2]")
        self.assertIn("SHOT_CUT_TIME_MISSING", codes(checker.audit(bad2)))
        bad3 = VALID.replace("[Shot 2] At 00:05.000", "[Shot 2] At 00:12.000")
        self.assertIn("SHOT_CUT_TIME_RANGE", codes(checker.audit(bad3, duration_seconds=10)))

    def test_speaker_order_and_empty_dialogue(self):
        bad = VALID.replace("(S1) turns", "(S2) turns")
        self.assertIn("SPEAKER_NUMBERING", codes(checker.audit(bad)))
        empty = VALID.replace("<d>[Mandarin] 会议开始。</d>", "<d>[Mandarin] </d>")
        self.assertIn("DIALOGUE_EMPTY", codes(checker.audit(empty)))

    def test_task_type_and_unused_label_are_review_items(self):
        bad = VALID.replace("[reference generation + audio reference]", "[magic]")
        report = checker.audit(bad)
        self.assertIn("TASK_TYPE_UNKNOWN", codes(report))
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        unused = VALID.replace("[Shot 2] At 00:05.000, the camera cuts to <Picture 1> as",
                               "[Shot 2] At 00:05.000, the camera cuts wider as")
        self.assertIn("DEFINED_LABEL_UNUSED", codes(checker.audit(unused)))

    def test_unpaired_continuity_tag_is_review(self):
        bad = VALID.replace("continues off-screen.", "continues <scenetrans> off-screen.")
        self.assertIn("CONTINUITY_TAG_UNPAIRED", codes(checker.audit(bad)))


if __name__ == "__main__":
    unittest.main()
