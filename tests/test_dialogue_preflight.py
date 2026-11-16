from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "dialogue_preflight",
    ROOT / "skills/produce-ai-video/scripts/dialogue_preflight.py")
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def codes(report):
    return {item["code"] for item in report["findings"]}


class DialoguePreflightTests(unittest.TestCase):
    def test_valid_official_syntax_passes(self):
        text = (
            "[Shot 1] Han Zheng, 52, with a low tired restrained male voice "
            "(S1) says: <d>[中文] 七年了。</d> His lips remain closed."
        )
        report = checker.audit(text)
        self.assertEqual(report["findings"], [], report["findings"])
        self.assertEqual(report["status"], "PASS")

    def test_no_dialogue_passes(self):
        report = checker.audit("[Shot 1] A man crosses the empty street at night.")
        self.assertEqual(report["status"], "PASS")

    def test_attribute_style_tag_blocks(self):
        text = "[Shot 1] Han Zheng (S1) says: <d zh>七年了。</d>"
        report = checker.audit(text)
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("DIALOGUE_ATTR_UNSUPPORTED", codes(report))

    def test_missing_language_tag_blocks(self):
        text = "[Shot 1] Han Zheng (S1) says: <d>七年了。</d>"
        report = checker.audit(text)
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("DIALOGUE_LANGUAGE_TAG", codes(report))

    def test_ellipsis_blocks(self):
        text = "[Shot 1] Han Zheng (S1) says: <d>[中文] ……七年了。</d>"
        report = checker.audit(text)
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("DIALOGUE_ELLIPSIS", codes(report))

    def test_speaker_id_and_says_required(self):
        text = "[Shot 1] Han Zheng says: <d>[中文] 七年了。</d>"
        report = checker.audit(text)
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("SPEAKER_ID_MISSING", codes(report))
        text = "[Shot 1] Han Zheng (S1): <d>[中文] 七年了。</d>"
        report = checker.audit(text)
        self.assertIn("SAYS_VERB_MISSING", codes(report))

    def test_speaker_order_blocks(self):
        text = "[Shot 1] Shen Yuan (S2) says: <d>[中文] 韩队？</d>"
        report = checker.audit(text)
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("SPEAKER_ORDER", codes(report))

    def test_stage_direction_inside_dialogue_reviews(self):
        text = "[Shot 1] Shen Yuan (S1) says: <d>[中文] 韩队（低声）？</d>"
        report = checker.audit(text)
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertIn("DIALOGUE_STAGE_DIRECTION", codes(report))

    def test_multi_speaker_shot_reviews(self):
        text = (
            "[Shot 1] Shen Yuan, 32, guarded low voice (S1) says: "
            "<d>[中文] 韩队？</d> Han Zheng, 52, low tired voice (S2) says: "
            "<d>[中文] 沈远，方便说话吗？</d>"
        )
        report = checker.audit(text)
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertIn("MULTI_SPEAKER_SHOT", codes(report))

    def test_unbalanced_tags_block(self):
        text = "[Shot 1] Han Zheng (S1) says: <d>[中文] 七年了。"
        report = checker.audit(text)
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("DIALOGUE_TAG_UNBALANCED", codes(report))


if __name__ == "__main__":
    unittest.main()
