from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "media_qc", ROOT / "skills/produce-ai-video/scripts/media_qc.py")
qc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qc)


def probe_json(duration="8.0", width=1280, height=720, fps="24/1", audio=True):
    streams = [{"codec_type": "video", "width": width, "height": height,
                "avg_frame_rate": fps, "duration": duration}]
    if audio:
        streams.append({"codec_type": "audio", "duration": duration})
    return json.dumps({"streams": streams, "format": {"duration": duration}})


def fake_runner(**outputs):
    """Return a runner that answers by matching a substring of the command."""
    def run(command, timeout=120):
        joined = " ".join(command)
        for key, (code, out, err) in outputs.items():
            if key in joined:
                return code, out, err
        return 0, "", ""
    return run


CLEAN = {
    "-show_streams": (0, probe_json(), ""),
    "blackdetect": (0, "", ""),
    "freezedetect": (0, "", ""),
    "volumedetect": (0, "", "mean_volume: -24.0 dB\nmax_volume: -3.0 dB"),
    "ebur128": (0, "", "I:   -16.0 LUFS"),
}


def codes(report):
    return {item["code"] for item in report["findings"]}


class MediaQcTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.media = Path(self.tmp.name) / "clip.mp4"
        self.media.write_bytes(b"synthetic media")

    def test_clean_clip(self):
        report = qc.audit(str(self.media), expect_duration=8.0,
                          expect_size=(1280, 720), expect_fps=24.0,
                          runner=fake_runner(**CLEAN))
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertEqual(report["semantic_review"], "not_performed")
        self.assertEqual(report["measurements"]["integrated_lufs"], -16.0)

    def test_unprobeable_blocks(self):
        runner = fake_runner(**{"-show_streams": (1, "", "err")})
        report = qc.audit(str(self.media), runner=runner)
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("CONTAINER_UNREADABLE", codes(report))

    def test_duration_and_resolution_mismatch(self):
        runner = fake_runner(**CLEAN)
        report = qc.audit(str(self.media), expect_duration=10.0,
                          expect_size=(1920, 1080), runner=runner)
        self.assertIn("DURATION_MISMATCH", codes(report))
        self.assertIn("RESOLUTION_MISMATCH", codes(report))

    def test_missing_audio_when_dialogue_expected(self):
        outputs = dict(CLEAN)
        outputs["-show_streams"] = (0, probe_json(audio=False), "")
        report = qc.audit(str(self.media), expect_dialogue=True,
                          runner=fake_runner(**outputs))
        finding = next(f for f in report["findings"]
                       if f["code"] == "AUDIO_STREAM_MISSING")
        self.assertEqual(finding["severity"], "block")

    def test_black_and_frozen_frames(self):
        outputs = dict(CLEAN)
        outputs["blackdetect"] = (0, "",
                                  "black_start:1.0 black_end:3.0\n")
        outputs["freezedetect"] = (0, "",
                                   "freeze_start: 4.0\nfreeze_end: 7.0\n")
        report = qc.audit(str(self.media), expect_duration=8.0,
                          runner=fake_runner(**outputs))
        black = next(f for f in report["findings"] if f["code"] == "BLACK_FRAMES")
        self.assertEqual(black["severity"], "block")  # 2s of 8s > 15%
        self.assertIn("FROZEN_FRAMES", codes(report))  # 3s of 8s > 30%

    def test_silent_audio_and_loudness(self):
        outputs = dict(CLEAN)
        outputs["volumedetect"] = (0, "", "mean_volume: -80.0 dB\nmax_volume: -70.0 dB")
        outputs["ebur128"] = (0, "", "I:   -40.0 LUFS")
        report = qc.audit(str(self.media), expect_dialogue=True,
                          runner=fake_runner(**outputs))
        self.assertIn("AUDIO_SILENT", codes(report))
        self.assertIn("LOUDNESS_OUT_OF_RANGE", codes(report))

    def test_subtitle_coverage(self):
        srt = ("1\n00:00:01,000 --> 00:00:04,000\n会议开始。\n\n"
               "2\n00:00:05,000 --> 00:00:09,900\n后半句。\n")
        dialogue = [{"text": "会议开始。"}, {"text": "缺失的台词"}]
        report = qc.audit(str(self.media), expect_duration=8.0, srt_text=srt,
                          dialogue=dialogue, runner=fake_runner(**CLEAN))
        self.assertIn("SUBTITLE_OUT_OF_RANGE", codes(report))
        self.assertIn("SUBTITLE_DIALOGUE_MISSING", codes(report))
        good = qc.audit(str(self.media), expect_duration=8.0,
                        srt_text=srt.replace("00:00:09,900", "00:00:07,000"),
                        dialogue=dialogue[:1], runner=fake_runner(**CLEAN))
        self.assertEqual(good["findings"], [])


if __name__ == "__main__":
    unittest.main()
