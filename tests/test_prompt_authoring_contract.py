from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_skill_guides import merge_contract


PROMPT_FAMILIES = {
    "director", "storyboard", "asset", "genre", "video-production", "orchestration",
    "short-drama", "hard-scifi", "war_visual", "guofeng",
}
AUTHORING_REFERENCES = (
    "skills/ai-storyboard-director/references/production-contract.md",
    "skills/ai-short-drama-production/references/production-handoff.md",
    "skills/produce-ai-video/references/storyboard-prompt-compiler.md",
    "skills/produce-ai-video/references/prompt-compilation-preflight.md",
)


class PromptAuthoringContractTests(unittest.TestCase):
    def setUp(self):
        self.contracts = json.loads((ROOT / "docs/skill-contracts.json").read_text(encoding="utf-8"))
        self.skills = [item for item in self.contracts["skills"] if item["family"] in PROMPT_FAMILIES]

    def test_each_standalone_prompt_skill_has_the_hard_rule_in_its_entry(self):
        self.assertTrue(self.skills)
        for item in self.skills:
            base = "experimental" if item["status"] == "experimental" else "skills"
            text = (ROOT / base / item["name"] / "SKILL.md").read_text(encoding="utf-8")
            with self.subTest(skill=item["name"]):
                self.assertIn("## 提示词逐项创作硬规则", text)
                self.assertIn("禁止编写或运行批量生成提示词的脚本", text)
                self.assertIn("循环套模板、变量替换、片段拼接", text)
                self.assertIn("批量调用模型", text)
                self.assertIn("逐项理解、逐项撰写、逐项复核", text)
                self.assertIn("原样保存", text)
                self.assertIn("不得生成、补写、改写或拼装提示词正文", text)
                self.assertIn("不能以逐条循环、拆成多个单次脚本", text)
                self.assertIn("不得交付或提交生成", text)

    def test_authoring_contracts_do_not_treat_compilation_as_script_permission(self):
        for relative in AUTHORING_REFERENCES:
            with self.subTest(path=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("禁止编写或运行批量生成提示词的脚本", text)
                self.assertIn("不授权脚本生成提示词", text)

    def test_batch_media_gate_cannot_waive_the_prompt_authoring_rule(self):
        text = (ROOT / "skills/produce-ai-video/references/pregeneration-quality-gate.md").read_text(encoding="utf-8")
        self.assertIn("本门只授权质量合格后的媒体批量执行", text)
        self.assertIn("不授权脚本生成提示词", text)

    def test_bilingual_guides_explain_the_same_boundary_for_every_prompt_skill(self):
        for item in self.skills:
            boundaries = merge_contract(self.contracts, item)["boundaries"]
            with self.subTest(skill=item["name"]):
                self.assertTrue(any("禁止编写或运行批量生成提示词的脚本" in entry["zh-CN"]
                                    and "Do not write or run scripts" in entry["en"]
                                    for entry in boundaries))
