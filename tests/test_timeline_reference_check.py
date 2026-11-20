"""Segment image lists must cover the subjects and space the prompt names."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "timeline_reference_check",
    ROOT / "skills" / "produce-ai-video" / "scripts" / "timeline_reference_check.py")
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def timeline(segment_images, prompt):
    return {
        "images": [
            {"id": "img-1", "file": "a_face.png", "name": "a_face.png"},
            {"id": "img-2", "file": "s01_room.png", "name": "s01_room.png"},
        ],
        "segmentConfig": {"segments": [
            {"startFrame": 0, "endFrame": 124, "images": segment_images, "prompt": prompt}]},
    }


PROMPT = ("<Picture 1> is <Subject 1> (S1), A.\n"
          "<Picture 2> is the room.\n"
          "detailed_description:\n[Shot 1] A sits at the table in the room.")


class TimelineReferenceTests(unittest.TestCase):
    def codes(self, tl):
        return {f["code"] for f in checker.check(tl)}

    def test_complete_refs_pass(self):
        self.assertEqual(self.codes(timeline(["img-1", "img-2"], PROMPT)), set())

    def test_picture_out_of_range_blocks(self):
        prompt = ("<Picture 1> is the room.\n<Picture 2> is <Subject 1> (S1), A.\n"
                  "detailed_description:\n[Shot 1] A in the room.")
        self.assertIn("PICTURE_OUT_OF_RANGE", self.codes(timeline(["img-2"], prompt)))

    def test_ref_role_mismatch_blocks(self):
        prompt = ("<Picture 1> is <Subject 1> (S1), A's face.\n<Picture 2> is the room.\n"
                  "detailed_description:\n[Shot 1] A in the room.")
        self.assertIn("REF_ROLE_MISMATCH", self.codes(timeline(["img-2", "img-2"], prompt)))

    def test_missing_scene_ref_blocks(self):
        self.assertIn("MISSING_SCENE_REF", self.codes(timeline(["img-1"], PROMPT)))

    def test_all_global_refs_is_review(self):
        tl = timeline(["img-1", "img-2"], PROMPT)
        tl["images"].append({"id": "img-3", "file": "b_face.png", "name": "b_face.png"})
        tl["images"].append({"id": "img-4", "file": "c_face.png", "name": "c_face.png"})
        tl["images"].append({"id": "img-5", "file": "d_face.png", "name": "d_face.png"})
        tl["segmentConfig"]["segments"][0]["images"] = ["img-1", "img-2", "img-3", "img-4", "img-5"]
        codes = self.codes(tl)
        self.assertIn("ALL_REFS_ATTACHED", codes)

    def test_missing_voice_anchor_blocks(self):
        tl = timeline(["img-1", "img-2"], PROMPT.replace(
            "detailed_description:\n[Shot 1] A sits at the table in the room.",
            "detailed_description:\n[Shot 1] A sits at the table in the room. "
            "<Subject 1> (S1) says, <d>[Chinese] 一。</d>"))
        self.assertIn("MISSING_VOICE_ANCHOR", self.codes(tl))

    def test_missing_audio_ref_blocks(self):
        prompt = PROMPT.replace(
            "detailed_description:\n[Shot 1] A sits at the table in the room.",
            ("<Audio 1> is the voice-timbre reference for <Subject 1> (S1). "
             "detailed_description:\n[Shot 1] A sits at the table in the room. "
             "<Subject 1> (S1) says, <d>[Chinese] 一。</d>"))
        tl = timeline(["img-1", "img-2"], prompt)
        tl["audios"] = [{"id": "aud-1", "file": "a.wav", "name": "a.wav",
                         "audioMode": "reference", "trimStart": 0, "duration": 2.0}]
        self.assertIn("AUDIO_OUT_OF_RANGE", self.codes(tl))

    def test_named_character_without_def_blocks(self):
        prompt = ("<Picture 1> is the room.\n"
                  "detailed_description:\n[Shot 1] Shen Guodong sits in the room.")
        self.assertIn("MISSING_SUBJECT_DEF", self.codes(timeline(["img-2"], prompt)))

    def test_video_reference_without_clip_blocks(self):
        prompt = PROMPT + "\n<Video 1> is the preceding shot."
        self.assertIn("NO_VIDEO_ANCHOR", self.codes(timeline(["img-1", "img-2"], prompt)))

    def test_bad_segment_length_blocks(self):
        tl = timeline(["img-1", "img-2"], PROMPT)
        tl["segmentConfig"]["segments"][0]["endFrame"] = 100
        self.assertIn("BAD_SEGMENT_LENGTH", self.codes(tl))

    def test_invalid_overlap_blocks(self):
        tl = timeline(["img-1", "img-2"], PROMPT)
        seg = tl["segmentConfig"]["segments"][0]
        tl["segmentConfig"]["segments"].append(dict(seg))
        tl["segmentConfig"]["segments"][1]["startFrame"] = seg["endFrame"] - 10
        tl["segmentConfig"]["segments"][1]["endFrame"] = seg["endFrame"] - 10 + 124
        self.assertIn("TRANSITION_OVERLAP_INVALID", self.codes(tl))


if __name__ == "__main__":
    unittest.main()
