import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = (Path(__file__).resolve().parents[1] /
          "skills/produce-ai-video/scripts/dialogue_content_check.py")
LINE = "这份合同明天上午交给我，在签字之前一定要先把附件全部确认清楚。"


class DialogueContentTests(unittest.TestCase):
    def check_dialogue(self, expected, heard, *options):
        with tempfile.TemporaryDirectory() as tmp:
            plan = Path(tmp) / "plan.json"
            asr = Path(tmp) / "asr.json"
            plan.write_text(json.dumps({"scenes": [{"id": "S1", "shots": [
                {"id": "01", "speaker": "A", "line": expected}
            ]}]}), encoding="utf-8")
            asr.write_text(json.dumps({"shots": {"01": heard}}), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "--plan", str(plan), "--asr", str(asr), *options],
                capture_output=True, text=True, encoding="utf-8",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
        return proc.returncode, json.loads(proc.stdout)

    def test_normalised_match_passes(self):
        code, report = self.check_dialogue(LINE, LINE.replace("，", " ").rstrip("。"))
        self.assertEqual((code, report["status"]), (0, "PASS"))

    def test_single_negation_requires_audio_review(self):
        code, report = self.check_dialogue(LINE, LINE.replace("一定要", "一定不要"))
        self.assertEqual((code, report["status"]), (3, "REVIEW_REQUIRED"))
        self.assertGreater(report["results"][0]["score"], 0.95)

    def test_decimal_and_word_boundaries_are_preserved(self):
        for expected, heard in [
            ("请将货款的1.5万元于明天下午打入对公账户", "请将货款的15万元于明天下午打入对公账户"),
            ("Please let me know if it says nowhere on the receipt.",
             "Please let me know if it says now here on the receipt."),
        ]:
            with self.subTest(expected=expected):
                code, report = self.check_dialogue(expected, heard)
                self.assertEqual((code, report["status"]), (3, "REVIEW_REQUIRED"))

    def test_unrelated_and_missing_dialogue_block(self):
        for heard in ("谁把门关上了", ""):
            with self.subTest(heard=heard):
                code, report = self.check_dialogue(LINE, heard)
                self.assertEqual((code, report["status"]), (1, "BLOCKED"))
        code, report = self.check_dialogue(LINE, "", "--allow-missing")
        self.assertEqual((code, report["status"]), (3, "REVIEW_REQUIRED"))
