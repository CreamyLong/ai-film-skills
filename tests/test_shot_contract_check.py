"""Structural shot-contract checks must catch known rework causes."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "produce-ai-video" / "scripts" / "shot_contract_check.py"
SPEC = importlib.util.spec_from_file_location("shot_contract_check", SCRIPT)
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def codes(shot):
    return {f["code"] for f in gate.audit_shot(shot)}


def ref(tag, file, role="identity"):
    return {"tag": tag, "file": file, "role": role}


class ShotContractTests(unittest.TestCase):
    def test_clean_single_speaker_shot_passes(self):
        shot = {"shot": "01", "refs": [
            ref(1, "assets/characters/a_hero.png"),
            ref(2, "assets/characters/a_face.png"),
            ref(3, "assets/scenes/room.png", "environment")],
            "prompt": (
                "subject_definitions:\n<Picture 1> is <Subject 1> (S1), A.\n"
                "<Picture 2> is <Subject 1>'s face.\n"
                "<Picture 3> is the room.\n"
                "detailed_description:\n[Shot 1] Medium close-up. A sits at the table and speaks.\n"
                "<Subject 1> (S1) says, <d>[Chinese] 你好。</d>")}
        self.assertEqual(gate.audit_shot(shot), [])

    def test_picture_count_mismatch_blocks(self):
        shot = {"shot": "02", "refs": [ref(1, "a_face.png")],
                "prompt": "<Picture 2> is the room.\ndetailed_description:\n[Shot 1] A room."}
        self.assertIn("PICTURE_COUNT_MISMATCH", codes(shot))

    def test_portrait_labelled_as_detail_blocks(self):
        shot = {"shot": "03", "refs": [ref(1, "shenguodong_hero.png")],
                "prompt": "<Picture 1> isolates the scar.\ndetailed_description:\n[Shot 1] Face."}
        self.assertIn("DETAIL_REF_IS_PORTRAIT", codes(shot))

    def test_alternating_speakers_is_review_not_block(self):
        shot = {"shot": "04", "refs": [ref(1, "a_face.png"), ref(2, "b_face.png")],
                "prompt": ("<Picture 1> is <Subject 1> (S1), A.\n<Picture 2> is <Subject 2> (S2), B.\n"
                           "detailed_description:\n[Shot 1] Two-shot in a room.\n"
                           "<Subject 1> (S1) says, <d>[Chinese] 一。</d> "
                           "<Subject 2> (S2) says, <d>[Chinese] 二。</d>")}
        findings = gate.audit_shot(shot)
        self.assertIn("ALTERNATING_SPEAKERS", {f["code"] for f in findings})
        self.assertEqual({f["severity"] for f in findings if f["code"] == "ALTERNATING_SPEAKERS"}, {"review"})

    def test_dialogue_plus_prop_action_blocks(self):
        shot = {"shot": "05", "refs": [ref(1, "a_face.png"), ref(2, "room.png", "environment")],
                "prompt": ("<Picture 1> is <Subject 1> (S1), A.\n<Picture 2> is the room.\n"
                           "detailed_description:\n[Shot 1] A sits at the table, pulls the drawer open "
                           "and sets a folder down.\n<Subject 1> (S1) says, <d>[Chinese] 一。</d>")}
        self.assertIn("DIALOGUE_PLUS_PROP_ACTION", codes(shot))

    def test_open_file_in_closeup_blocks(self):
        shot = {"shot": "06", "refs": [ref(1, "room.png", "environment")],
                "prompt": ("<Picture 1> is the room.\ndetailed_description:\n"
                           "[Shot 1] Close-up of hands holding an open file, the title visible.")}
        self.assertIn("TEXT_PROP_IN_CLOSEUP", codes(shot))
        self.assertEqual({f["severity"] for f in gate.audit_shot(shot)
                          if f["code"] == "TEXT_PROP_IN_CLOSEUP"}, {"block"})

    def test_missing_environment_anchor_blocks(self):
        shot = {"shot": "07", "refs": [ref(1, "a_face.png")],
                "prompt": ("<Picture 1> is <Subject 1> (S1), A.\ndetailed_description:\n"
                           "[Shot 1] A sits at the table in the room.")}
        self.assertIn("MISSING_ENVIRONMENT_ANCHOR", codes(shot))

    def test_unanchored_foreground_person_blocks(self):
        shot = {"shot": "08", "refs": [ref(1, "a_face.png"), ref(2, "room.png", "environment")],
                "prompt": ("<Picture 1> is <Subject 1> (S1), A.\n<Picture 2> is the room.\n"
                           "detailed_description:\n[Shot 1] Close-up over B's shoulder onto A at the table.")}
        self.assertIn("UNANCHORED_FOREGROUND_PERSON", codes(shot))


if __name__ == "__main__":
    unittest.main()
