"""Regression guards for H3 prompt/continuity guidance consistency."""

from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RuntimeConsistencyTests(unittest.TestCase):
    def all_skill_text(self) -> str:
        return "\n".join(path.read_text(encoding="utf-8")
                         for path in ROOT.glob("skills/**/*.md"))

    def test_no_legacy_dialogue_tag_variants(self):
        self.assertNotIn("<d zh>", self.all_skill_text())

    def test_caption_qc_uses_six_frames(self):
        text = (ROOT / "skills" / "produce-ai-video" / "references" /
                "prompt-compilation-preflight.md").read_text(encoding="utf-8")
        self.assertIn("生成六帧联系表", text)
        self.assertNotIn("生成三帧联系表", text)

    def test_no_official_multi_angle_myth(self):
        text = self.all_skill_text()
        self.assertNotIn("真正的换机位/换场拆开单独生成", text)
        self.assertIn("h3-official-prompt-contract.md",
                      (ROOT / "skills" / "produce-ai-video" / "SKILL.md").read_text(encoding="utf-8"))

    def test_no_global_single_bed_rule(self):
        self.assertNotIn("整片铺一条低电平房间声底", self.all_skill_text())

    def test_long_segment_and_scheduler_rules_exist(self):
        text = self.all_skill_text()
        self.assertIn("单段不要超过 362 帧", text)
        self.assertIn("turbo 4-step LoRA 必须配 `simple`", text)


if __name__ == "__main__":
    unittest.main()
