from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "h3_base_check", ROOT / "skills/produce-ai-video/scripts/h3_base_check.py")
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)

T2VA = """integrated_multimodal_description: [Shot 1] Live-action, cinematic, a medium-wide shot frames a baker opening the shutters. The baker with a calm voice (S1) says: <d>[English] First batch.</d> [Shot 2] At 00:05.000, the camera cuts to steam rising from the bread.

overall_soundscape: Wooden shutters scrape open over a quiet street.

non_diegetic_music: N/A
"""

I2VA = """For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.

integrated_multimodal_description: [Shot 1] Live-action, cinematic, the young woman shown in <Picture 1> remains beside the window. She says with a quiet voice (S1): <d>[English] I get off at the next station.</d>

overall_soundscape: The train wheels produce a steady rhythm.

non_diegetic_music: Sustained cello notes at a slow tempo.
"""

FL2VA = """How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot 1) aligns with the 8.00-second mark of the target video.

integrated_multimodal_description: [Shot 1] Live-action, cinematic, a cyclist begins in the framing of Picture 1 and settles into the pose of Picture 2 at the end of the shot.

overall_soundscape: Rain falls steadily on the pavement.

non_diegetic_music: N/A
"""

L2VA = """How the reference pictures align with the target video — <Picture 1> (from [Shot 1]) aligns with the 6.00-second mark of the target video.

integrated_multimodal_description: [Shot 1] Live-action, cinematic, a glass tips and breaks, the fragments settling into the arrangement of <Picture 1>.

overall_soundscape: The glass scrapes, falls, and breaks with a sharp crash.

non_diegetic_music: A low electronic pulse at a slow tempo.
"""


def codes(report):
    return {item["code"] for item in report["findings"]}


class H3BaseCheckTests(unittest.TestCase):
    def test_valid_modes_have_no_findings(self):
        for text, mode, duration in ((T2VA, "t2va", None),
                                     (I2VA, "i2va", None),
                                     (FL2VA, "fl2va", 8.0),
                                     (L2VA, "l2va", 6.0)):
            report = checker.audit(text, mode, duration_seconds=duration)
            self.assertEqual(report["findings"], [], f"{mode}: {report['findings']}")
            self.assertEqual(report["status"], "REVIEW_REQUIRED")

    def test_unknown_mode_blocks(self):
        report = checker.audit(T2VA, "ref2va")
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("MODE_UNKNOWN", codes(report))

    def test_missing_instruction_blocks(self):
        report = checker.audit(T2VA, "i2va")
        self.assertIn("INSTRUCTION_MISSING", codes(report))
        report = checker.audit(I2VA, "t2va")
        self.assertIn("INSTRUCTION_UNEXPECTED", codes(report))

    def test_instruction_alignment_mismatch(self):
        bad = FL2VA.replace("Shot 1) aligns with the 8.00", "Shot 2) aligns with the 8.00")
        self.assertIn("INSTRUCTION_SHOT_MISMATCH", codes(checker.audit(bad, "fl2va", 8.0)))
        bad = L2VA.replace("6.00-second", "5.00-second")
        self.assertIn("INSTRUCTION_TIME_MISMATCH", codes(checker.audit(bad, "l2va", 6.0)))

    def test_missing_field_blocks(self):
        report = checker.audit(T2VA.replace("overall_soundscape:", "notes:"), "t2va")
        self.assertIn("FIELD_STRUCTURE", codes(report))

    def test_mixed_ref2va_section_blocks(self):
        bad = T2VA + "\nretention_analysis:\n<Picture 1>: fully_preserved - kept.\n"
        self.assertIn("SECTION_MIXED_FORMAT", codes(checker.audit(bad, "t2va")))

    def test_label_rules(self):
        bad = T2VA.replace("a baker opening", "<Subject 1> opening")
        self.assertIn("LABEL_FORBIDDEN", codes(checker.audit(bad, "t2va")))
        bad = T2VA.replace("the shutters", "the shutters of <Picture 1>")
        self.assertIn("PICTURE_LABEL_UNEXPECTED", codes(checker.audit(bad, "t2va")))
        missing = I2VA.replace(" shown in <Picture 1>", "")
        self.assertIn("PICTURE_LABEL_MISSING", codes(checker.audit(missing, "i2va")))

    def test_shot_and_speaker_rules(self):
        bad = T2VA.replace("[Shot 2] At 00:05.000", "[Shot 2]")
        self.assertIn("SHOT_CUT_TIME_MISSING", codes(checker.audit(bad, "t2va")))
        bad = T2VA.replace("[Shot 2] At 00:05.000", "[Shot 2] At 00:09.000")
        self.assertIn("SHOT_CUT_TIME_RANGE", codes(checker.audit(bad, "t2va", 8.0)))
        bad = T2VA.replace("(S1)", "(S2)")
        self.assertIn("SPEAKER_NUMBERING", codes(checker.audit(bad, "t2va")))
        empty = T2VA.replace("<d>[English] First batch.</d>", "<d>[English] </d>")
        self.assertIn("DIALOGUE_EMPTY", codes(checker.audit(empty, "t2va")))


if __name__ == "__main__":
    unittest.main()
