from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "caption_preflight", ROOT / "skills/produce-ai-video/scripts/caption_preflight.py")
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def codes(prompt, mode="native"):
    return {(item["code"], item["severity"]) for item in gate.check_prompt(prompt, mode)}


class CaptionPreflightTests(unittest.TestCase):
    def test_negative_subtitle_wording_blocks(self):
        self.assertIn(("TEXT_PRIMING", "block"),
                      codes("A clean close-up. No subtitles, no watermark."))

    def test_technical_specs_and_speaker_id_block(self):
        for text in ("vertical 9:16 scene", "24fps", "Speaker ID: Han", "768x1344"):
            with self.subTest(text=text):
                self.assertIn(("TECH_SPEC_TEXT", "block"), codes(text))

    def test_quoted_dialogue_is_review_for_native_and_block_for_silent(self):
        prompt = 'He says: "你签的。"'
        self.assertIn(("QUOTED_DIALOGUE_TEXT", "review"), codes(prompt, "native"))
        self.assertIn(("QUOTED_DIALOGUE_TEXT", "block"), codes(prompt, "silent"))

    def test_clean_silent_prompt_passes(self):
        self.assertEqual(codes("A medium two-shot in a warehouse, footsteps, cold light.", "silent"), set())


if __name__ == "__main__":
    unittest.main()
