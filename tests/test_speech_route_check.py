from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "speech_route_check", ROOT / "skills/produce-ai-video/scripts/speech_route_check.py")
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


class SpeechRouteCheckTests(unittest.TestCase):
    def test_visible_speech_without_audio_blocks(self):
        self.assertEqual(
            [f["code"] for f in gate.check_speech_route(
                "Tight close-up. He speaks, lips moving.", [])],
            ["POST_DUB_SPEAKING_FACE"])

    def test_locked_or_reference_audio_passes(self):
        for refs in ([{"mode": "locked"}], [{"mode": "reference"}]):
            with self.subTest(refs=refs):
                self.assertEqual(gate.check_speech_route("He speaks, lips moving.", refs), [])

    def test_lips_closed_listener_passes(self):
        self.assertEqual(gate.check_speech_route("He listens, lips closed.", []), [])

    def test_lips_parting_without_speech_passes(self):
        self.assertEqual(gate.check_speech_route("His lips part slightly, then close.", []), [])


if __name__ == "__main__":
    unittest.main()
