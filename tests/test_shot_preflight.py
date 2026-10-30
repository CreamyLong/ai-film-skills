from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "skills/produce-ai-video/scripts/shot_preflight.py"
SPEC = importlib.util.spec_from_file_location("shot_preflight", CLI)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def sample():
    return {
        "schema": checker.SCHEMA,
        "tracked_items": ["parcel"],
        "shots": [
            {
                "id": "S01", "duration_seconds": 4,
                "prompt": "Mira places the parcel on the table. Mira says: Take it.",
                "audio_route": "native", "dialogue": [{"speaker": "Mira", "text": "Take it."}],
                "speech_timing": {"measured_seconds": 1.2, "window_seconds": 2,
                                  "basis": "timed read", "cross_shot": False},
                "entry_state": {"parcel": "Mira"}, "exit_state": {"parcel": "table"},
                "state_actions": {"parcel": "Mira places the parcel on the table."},
            },
            {
                "id": "S02", "duration_seconds": 4, "prompt": "Mira picks up the parcel.",
                "audio_route": "silent", "dialogue": [], "transition": "cut",
                "entry_state": {"parcel": "table"}, "exit_state": {"parcel": "Mira"},
                "previous_tail_claim": {"parcel": "table"},
                "state_actions": {"parcel": "Mira picks up the parcel."},
            },
        ],
    }


def codes(result):
    return {item["code"] for item in result["findings"]}


class ShotPreflightTests(unittest.TestCase):
    def test_no_finding_is_not_semantic_or_submission_approval(self):
        result = checker.audit(sample())
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["semantic_review"], "not_performed")
        self.assertEqual(result["asset_review"], "not_performed")
        self.assertFalse(result["actual_model_submission_checked"])

    def test_native_dialogue_must_be_in_actual_video_prompt(self):
        data = sample()
        data["shots"][0]["prompt"] = "Mira places the parcel on the table. She speaks."
        result = checker.audit(data)
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("DIALOGUE_NOT_MAPPED", codes(result))

    def test_external_dialogue_can_be_in_external_audio_task(self):
        data = sample()
        shot = data["shots"][0]
        shot.update(prompt="Mira places the parcel on the table.",
                    audio_route="external", audio_prompt="Mira says: Take it.")
        self.assertNotIn("DIALOGUE_NOT_MAPPED", codes(checker.audit(data)))
        shot["audio_prompt"] = "Mira speaks."
        self.assertIn("DIALOGUE_NOT_MAPPED", codes(checker.audit(data)))
        shot["audio_route"] = "silent"
        self.assertIn("DIALOGUE_NOT_MAPPED", codes(checker.audit(data)))

    def test_timing_requires_evidence_and_supports_cross_shot_audio(self):
        data = sample()
        timing = data["shots"][0]["speech_timing"]
        timing["measured_seconds"] = 5
        self.assertIn("SPEECH_WINDOW_OVERRUN", codes(checker.audit(data)))
        timing.update(window_seconds=6, cross_shot=True)
        result = checker.audit(data)
        self.assertNotIn("SPEECH_WINDOW_OVERRUN", codes(result))
        self.assertIn("CROSS_SHOT_TIMING_UNVERIFIED", codes(result))
        timing["cross_shot"] = False
        with self.assertRaises(checker.InputError):
            checker.audit(data)
        del data["shots"][0]["speech_timing"]
        self.assertIn("SPEECH_TIMING_UNVERIFIED", codes(checker.audit(data)))

    def test_state_jump_and_transition_evidence(self):
        data = sample()
        second = data["shots"][1]
        second["entry_state"]["parcel"] = "Mira"
        second["exit_state"]["parcel"] = "Mira"
        second.pop("state_actions")
        result = checker.audit(data)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertIn("STATE_HANDOFF_UNEXPLAINED", codes(result))
        second["transition"] = "continuous"
        self.assertEqual(checker.audit(data)["status"], "BLOCK")
        second["transition"] = "ellipsis"
        second["entry_changes"] = {"parcel": "Retrieved during the time jump."}
        result = checker.audit(data)
        self.assertNotIn("STATE_HANDOFF_UNEXPLAINED", codes(result))
        self.assertIn("STATE_HANDOFF_REQUIRES_REVIEW", codes(result))

    def test_wrong_previous_tail_is_not_current_opening(self):
        data = sample()
        data["shots"][1]["previous_tail_claim"]["parcel"] = "Mira"
        result = checker.audit(data)
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("PREVIOUS_TAIL_MISMATCH", codes(result))

    def test_in_shot_change_requires_submitted_evidence(self):
        data = sample()
        data["shots"][1]["state_actions"]["parcel"] = "Mira retrieved it offscreen."
        self.assertIn("STATE_ACTION_UNVERIFIED", codes(checker.audit(data)))
        data["shots"][1]["exit_state"]["parcel"] = None
        self.assertIn("STATE_UNVERIFIED", codes(checker.audit(data)))

    def test_reusing_initial_frame_for_continuous_shot_is_a_review_signal(self):
        data = sample()
        data["shots"][0]["initial_frame"] = "same-still"
        data["shots"][1].update(initial_frame="same-still", transition="continuous")
        self.assertIn("CONTINUOUS_START_FRAME_REUSED", codes(checker.audit(data)))
        data["shots"][1]["initial_frame"] = "actual-tail"
        self.assertNotIn("CONTINUOUS_START_FRAME_REUSED", codes(checker.audit(data)))

    def test_invalid_inputs_are_not_approved(self):
        for edit in (
            lambda x: x["shots"][0].update(duration_seconds=True),
            lambda x: x["shots"][0].update(duration_seconds=float("nan")),
            lambda x: x["shots"][1].update(id="S01"),
            lambda x: x["shots"][1]["entry_state"].clear(),
            lambda x: x["shots"][1].update(transition="unknown"),
            lambda x: x["shots"][0].update(unexpected=True),
        ):
            data = sample()
            edit(data)
            with self.assertRaises(checker.InputError):
                checker.audit(data)

    def test_cli_repair_changes_input_and_prompt_hash_and_requires_review(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.json"
            data = sample()
            data["shots"][0]["prompt"] = "Mira places the parcel on the table."

            def run():
                path.write_text(json.dumps(data), encoding="utf-8")
                result = subprocess.run([sys.executable, "-B", str(CLI), "--input", str(path)],
                                        capture_output=True, text=True, timeout=10)
                return result.returncode, json.loads(result.stdout)

            code, broken = run()
            self.assertEqual(code, 1)
            self.assertEqual(broken["status"], "BLOCK")
            data["shots"][0]["prompt"] += " Mira says: Take it."
            code, repaired = run()
            self.assertEqual(code, 2)
            self.assertEqual(repaired["status"], "REVIEW_REQUIRED")
            self.assertNotEqual(broken["input_sha256"], repaired["input_sha256"])
            self.assertNotEqual(broken["prompts"][0]["prompt_sha256"],
                                repaired["prompts"][0]["prompt_sha256"])

    def test_declared_data_does_not_validate_a_fabricated_story(self):
        data = copy.deepcopy(sample())
        data["shots"][0]["entry_state"]["parcel"] = "unknown impossible history"
        result = checker.audit(data)
        self.assertEqual(result["semantic_review"], "not_performed")
        self.assertEqual(result["status"], "REVIEW_REQUIRED")


if __name__ == "__main__":
    unittest.main()
