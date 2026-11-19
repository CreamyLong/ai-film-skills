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

    def test_submission_rules_are_scoped_to_the_selected_runtime(self):
        skill = ROOT / "skills" / "produce-ai-video"
        entry = (skill / "SKILL.md").read_text(encoding="utf-8")
        lines = entry.splitlines()
        common = next(line for line in lines if "**Every provider and retry:**" in line)
        prompt = next(line for line in lines if "**Prompt format:**" in line)
        runtime = next(line for line in lines if "**Execution runtime:**" in line)
        for h3_only in ("h3-official-prompt-contract.md", "submission_gateway.py", "prompt_id"):
            self.assertNotIn(h3_only, common)
        self.assertIn("only to H3 Ref2VA", prompt)
        self.assertIn("For other routes, use their verified", prompt)
        self.assertIn('with `h3_mode` and use `scripts/h3_base_check.py`', prompt)
        self.assertIn("Only on ComfyUI, read back", runtime)
        self.assertIn("For other graphs or providers, use a verified runtime adapter", runtime)
        self.assertNotIn("TimelineDirector", entry.splitlines()[2])

    def test_no_global_single_bed_rule(self):
        self.assertNotIn("整片铺一条低电平房间声底", self.all_skill_text())

    def test_long_segment_and_scheduler_rules_exist(self):
        text = self.all_skill_text()
        self.assertIn("单段不要超过 362 帧", text)
        self.assertIn("turbo 4-step LoRA 必须配 `simple`", text)


if __name__ == "__main__":
    unittest.main()
