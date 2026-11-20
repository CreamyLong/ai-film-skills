"""The story-bible gate must block episode writing on profile/motive/asset gaps."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "story_bible_check", ROOT / "skills" / "director-agent" / "scripts" / "story_bible_check.py")
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def bible(**chars):
    return {"characters": chars}


def entry(**kw):
    base = {"role": "support", "profile": "p", "asset_id": "C01"}
    base.update(kw)
    return base


class StoryBibleCheckTests(unittest.TestCase):
    def codes(self, findings):
        return {f["code"] for f in findings}

    def test_complete_cast_passes(self):
        b = bible(**{
            "韩峥": entry(role="protagonist"),
            "周启明": entry(role="antagonist", motive="m", resources="r", means="n"),
        })
        apps = [{"episode": "EP014", "character": "韩峥"},
                {"episode": "EP014", "character": "周启明", "speaks": True}]
        self.assertEqual(gate.check(b, apps), [])

    def test_appearing_character_without_profile_blocks(self):
        b = bible(韩峥=entry(role="protagonist"))
        apps = [{"episode": "EP014", "character": "周启明", "speaks": True}]
        codes = self.codes(gate.check(b, apps))
        self.assertIn("MISSING_PROFILE", codes)

    def test_antagonist_without_motive_blocks(self):
        b = bible(**{"韩峥": entry(role="protagonist"),
                     "周": entry(role="antagonist", resources="r", means="n")})
        apps = [{"episode": "EP014", "character": "周", "speaks": True}]
        codes = self.codes(gate.check(b, apps))
        self.assertIn("ANTAGONIST_NO_MOTIVE", codes)

    def test_appearing_character_without_asset_blocks(self):
        e = entry()
        del e["asset_id"]
        b = bible(**{"韩峥": entry(role="protagonist"), "陈": e})
        apps = [{"episode": "EP003", "character": "陈", "speaks": True}]
        self.assertIn("NO_LOCKED_ASSET", self.codes(gate.check(b, apps)))

    def test_cast_without_antagonist_is_review_not_block(self):
        b = bible(韩峥=entry(role="protagonist"))
        apps = [{"episode": "EP001", "character": "韩峥"}]
        findings = gate.check(b, apps)
        self.assertEqual([f["severity"] for f in findings], ["review"])


if __name__ == "__main__":
    unittest.main()
