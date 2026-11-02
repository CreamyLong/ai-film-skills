from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ProductionCompletionContractTests(unittest.TestCase):
    def test_new_contracts_are_reachable_from_standalone_entrypoints(self):
        cases = {
            "director-agent": ["series-and-performance.md"],
            "ai-short-drama-production": ["series-development.md", "series-bible.md"],
            "produce-ai-video": ["production-controls.md", "editorial-workflow.md",
                                 "finishing-and-delivery.md", "production-validation.md"],
        }
        for skill, references in cases.items():
            entry = (ROOT / "skills" / skill / "SKILL.md").read_text()
            for name in references:
                with self.subTest(skill=skill, reference=name):
                    self.assertIn(f"references/{name}", entry)
                    self.assertTrue((ROOT / "skills" / skill / "references" / name).is_file())

    def test_model_workarounds_do_not_reintroduce_universal_edit_rules(self):
        paths = [
            "skills/ai-storyboard-director/references/shot-size-rhythm.md",
            "skills/produce-ai-video/SKILL.md",
            "skills/produce-ai-video/references/segment-seam-continuity.md",
            "skills/produce-ai-video/references/qualified-video-acceptance.md",
        ]
        for relative in paths:
            text = (ROOT / relative).read_text()
            for obsolete in ("同档硬绑定", "单集不超过 3 处", "每加 1 秒买回约 6 字",
                             "open the first shot one stop wider"):
                with self.subTest(path=relative, obsolete=obsolete):
                    self.assertNotIn(obsolete, text)
        seams = (ROOT / paths[2]).read_text()
        for boundary in ("同镜续接", "正常切镜", "叙事跳跃", "工具余量"):
            self.assertIn(boundary, seams)

    def test_pregeneration_document_uses_the_checked_100_point_rubric(self):
        text = (ROOT / "skills/produce-ai-video/references/pregeneration-quality-gate.md").read_text()
        weights = re.findall(r"^\| [a-z_]+ \| (\d+) \|", text, re.MULTILINE)
        self.assertEqual(len(weights), 8)
        self.assertEqual(sum(map(int, weights)), 100)
        for required in ("quality_gate_check.py", "2分", "1分", "REVIEW_REQUIRED", "逐项"):
            self.assertIn(required, text)

    def test_new_workflows_do_not_imply_media_or_approval(self):
        paths = [
            "skills/director-agent/references/series-and-performance.md",
            "skills/ai-short-drama-production/references/series-development.md",
            "skills/produce-ai-video/references/editorial-workflow.md",
            "skills/produce-ai-video/references/production-validation.md",
        ]
        for relative in paths:
            text = (ROOT / relative).read_text()
            with self.subTest(path=relative):
                self.assertIn("授权", text)
                self.assertIn("逐项", text)
                self.assertIn("验证", text)
        validation = (ROOT / paths[-1]).read_text()
        for required in ("完整对白场景", "完整短片", "连续多集", "改稿与返工",
                         "not_performed", "user_acceptance", "不能将"):
            self.assertIn(required, validation)
