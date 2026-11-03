from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "timeline_plan_check", ROOT / "skills/produce-ai-video/scripts/timeline_plan_check.py")
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)

SHOT = "detailed_description:\n[Shot 1] The figure from <Picture 1> walks; <Audio 1> guides the voice."


def segmented(**overrides):
    timeline = {
        "version": 10,
        "selection": {"start": 0.0, "duration": 362 / 24},
        "images": [{"id": "i1", "file": "refs/a.png"}, {"id": "i2", "file": "refs/b.png"}],
        "audios": [{"id": "a1", "file": "voices/v.wav", "audioMode": "reference"}],
        "videoClips": [],
        "videoAudioEnabled": True,
        "globalPrompt": "",
        "secondPass": False,
        "segmentConfig": {"count": 2, "mode": "timeline", "segments": [
            {"startFrame": 0, "endFrame": 192, "images": ["i1", "i2"], "audios": ["a1"], "prompt": SHOT},
            {"startFrame": 170, "endFrame": 362, "images": ["i2"], "audios": ["a1"], "prompt": SHOT},
        ]},
    }
    timeline.update(overrides)
    return timeline


def codes(report):
    return {item["code"] for item in report["findings"]}


def run(timeline, **payload):
    return checker.audit({"timeline_data": timeline, "width": 1280, "height": 544, **payload})


class TimelinePlanCheckTest(unittest.TestCase):
    def test_clean_segmented_plan_labels_restart_per_segment(self):
        report = run(segmented())
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertEqual(codes(report), {"CONTINUATION_SHOT1_REVIEW"})
        second = report["segments"][1]
        self.assertEqual(second["overlap_frames"], 22)
        self.assertEqual(second["kept_frames"], 170)
        self.assertEqual([x["file"] for x in second["labels"]["pictures"]], ["refs/b.png"])
        self.assertEqual(report["audio_route"], "generate")
        self.assertEqual(report["target_output_frames"], 362)

    def test_valid_overlap_values(self):
        self.assertTrue(all(checker.valid_overlap(v) for v in (0, 1, 5, 22, 39, 48 - 9)))
        self.assertFalse(any(checker.valid_overlap(v) for v in (2, 24, 48)))

    def test_off_grid_length_and_bad_overlap_block(self):
        timeline = segmented()
        timeline["segmentConfig"]["segments"][0]["endFrame"] = 190
        timeline["segmentConfig"]["segments"][1].update(startFrame=166, endFrame=358)
        self.assertTrue({"SEGMENT_LENGTH_OFF_GRID", "SEGMENT_SEQUENCE_INVALID"} <= codes(run(timeline)))

    def test_gap_between_segments_blocks(self):
        timeline = segmented()
        timeline["segmentConfig"]["segments"][1].update(startFrame=200, endFrame=392)
        self.assertIn("SEGMENT_SEQUENCE_INVALID", codes(run(timeline)))

    def test_prompt_label_must_fit_segment_assets(self):
        timeline = segmented()
        timeline["segmentConfig"]["segments"][1]["prompt"] = SHOT.replace("<Picture 1>", "<Picture 2>")
        self.assertIn("PROMPT_LABEL_OUT_OF_RANGE", codes(run(timeline)))

    def test_partial_segment_prompts_block(self):
        timeline = segmented()
        timeline["segmentConfig"]["segments"][1]["prompt"] = ""
        self.assertIn("SEGMENT_PROMPTS_INCOMPLETE", codes(run(timeline)))

    def test_continuation_without_shot_one_blocks(self):
        timeline = segmented()
        timeline["segmentConfig"]["segments"][1]["prompt"] = "detailed_description:\nNew action."
        self.assertIn("CONTINUATION_SHOT1_MISSING", codes(run(timeline)))

    def test_unknown_segment_asset_and_capacity_block(self):
        timeline = segmented()
        timeline["images"] = [{"id": f"i{n}", "file": f"refs/{n}.png"} for n in range(1, 11)]
        timeline["segmentConfig"]["segments"][0]["images"] = [f"i{n}" for n in range(1, 11)]
        timeline["segmentConfig"]["segments"][1]["images"] = ["missing"]
        found = codes(run(timeline))
        self.assertIn("SEGMENT_CAPACITY_EXCEEDED", found)
        self.assertIn("SEGMENT_ASSET_UNKNOWN", found)

    def test_absolute_media_path_blocks(self):
        timeline = segmented()
        timeline["images"][0]["file"] = "/home/user/a.png"
        self.assertIn("MEDIA_PATH_OUTSIDE_INPUT", codes(run(timeline)))

    def test_implicit_video_fields_block(self):
        timeline = segmented()
        del timeline["videoAudioEnabled"]
        timeline["videoClips"] = [{"id": "v1", "file": "prev.mp4", "start": 6.0, "duration": 2.0}]
        found = codes(run(timeline))
        self.assertTrue({"REFERENCE_MODE_IMPLICIT", "CLIP_AUDIO_IMPLICIT", "VIDEO_AUDIO_IMPLICIT"} <= found)

    def test_video_soundtrack_locks_final_audio(self):
        timeline = segmented(videoClips=[{"id": "v1", "file": "prev.mp4", "start": 6.0, "duration": 2.0,
                                          "trimStart": 0.0, "hasAudio": True, "referenceMode": "guide"}])
        report = run(timeline)
        self.assertEqual(report["audio_route"], "video_original")
        self.assertIn("AUDIO_ROUTE_FIXED", codes(report))
        self.assertIn("AUDIO_ROUTE_MISMATCH", codes(run(timeline, audio_intent="generate")))

    def test_video_without_soundtrack_keeps_generation(self):
        timeline = segmented(videoClips=[{"id": "v1", "file": "prev.mp4", "start": 6.0, "duration": 2.0,
                                          "trimStart": 0.0, "hasAudio": False, "referenceMode": "guide"}])
        report = run(timeline, audio_intent="generate")
        self.assertEqual(report["audio_route"], "generate")
        first = report["segments"][0]
        self.assertEqual(first["labels"]["videos"][0]["label"], "<Video 1>")
        self.assertEqual(first["guides"][0]["kind"], "fixed_guide")
        self.assertEqual(first["guides"][0]["frames"], 48)

    def test_disabled_video_audio_mutes_output(self):
        timeline = segmented(videoAudioEnabled=False, videoClips=[{
            "id": "v1", "file": "prev.mp4", "start": 0.0, "duration": 4.0,
            "trimStart": 0.0, "hasAudio": True, "referenceMode": "edit"}])
        self.assertEqual(run(timeline)["audio_route"], "silent")

    def test_locked_audio_rules(self):
        timeline = segmented()
        timeline["audios"].append({"id": "lock", "file": "song.wav", "audioMode": "locked"})
        timeline["segmentConfig"]["segments"][0]["audios"] = ["a1", "lock"]
        self.assertIn("LOCKED_AUDIO_PARTIAL", codes(run(timeline)))
        timeline["segmentConfig"]["segments"][1]["audios"] = ["a1", "lock"]
        report = run(timeline, audio_intent="locked_audio")
        self.assertEqual(report["audio_route"], "locked_audio")
        self.assertEqual([x["label"] for x in report["segments"][0]["labels"]["audios"]], ["<Audio 1>"])
        self.assertNotIn("AUDIO_ROUTE_MISMATCH", codes(report))

    def test_short_intersection_and_long_clip_split(self):
        timeline = segmented(videoClips=[
            {"id": "tiny", "file": "t.mp4", "start": 7.95, "duration": 0.1, "trimStart": 0.0,
             "hasAudio": False, "referenceMode": "edit"}])
        self.assertIn("VIDEO_INTERSECTION_TOO_SHORT", codes(run(timeline)))
        single = {"selection": {"start": 0.0, "duration": 20.0}, "images": [], "audios": [],
                  "videoAudioEnabled": False, "globalPrompt": "x",
                  "videoClips": [{"id": "long", "file": "l.mp4", "start": 0.0, "duration": 30.0,
                                  "trimStart": 0.0, "hasAudio": False, "referenceMode": "edit"}]}
        report = run(single, generation_seconds=20.0)
        self.assertEqual(len(report["segments"][0]["labels"]["videos"]), 2)
        self.assertIn("VIDEO_REFERENCE_TOO_LONG", codes(report))

    def test_second_pass_constraints(self):
        timeline = segmented(secondPass=True, secondPassModel="", secondPassHighSteps=4)
        found = codes(run(timeline, sampler={"name": "res_multistep", "steps": 4}))
        self.assertTrue({"SECOND_PASS_MODEL_MISSING", "SECOND_PASS_STEPS_INVALID",
                         "SECOND_PASS_SAMPLER"} <= found)

    def test_director_runtime_rules(self):
        single = {"selection": {"start": 0.0, "duration": 5.0},
                  "images": [{"id": "i1", "file": "a.png"}], "audios": [], "videoClips": []}
        report = checker.audit({"runtime": "director", "timeline_data": single,
                                "generation_seconds": 5.0, "prompt": SHOT.replace(" <Audio 1>", "")})
        self.assertNotIn("PROMPT_MISSING", codes(report))
        self.assertEqual(report["segments"][0]["length"], 124)
        self.assertIn("SEGMENTS_NEED_FINITE_SAMPLER",
                      codes(checker.audit({"runtime": "director", "timeline_data": segmented(), "prompt": SHOT})))

    def test_invalid_json(self):
        self.assertIn("TIMELINE_INVALID", codes(checker.audit({"timeline_data": "{"})))

    def test_report_does_not_mutate_input(self):
        timeline = segmented()
        before = copy.deepcopy(timeline)
        run(timeline)
        self.assertEqual(timeline, before)


if __name__ == "__main__":
    unittest.main()
