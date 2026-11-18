from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "generation_asset_gc", ROOT / "skills/produce-ai-video/scripts/generation_asset_gc.py")
gc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gc)


class GenerationAssetGCTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.generated = self.root / "EP007/video/v1"
        self.generated.mkdir(parents=True)
        (self.root / "EP007/edit").mkdir(parents=True)
        self.accepted = self.generated / "shot07_fix.mp4"
        self.accepted.write_bytes(b"accepted")
        self.rejected = self.generated / "shot07.mp4"
        self.rejected.write_bytes(b"rejected")
        old = time.time() - 3 * 86400
        os.utime(self.rejected, (old, old))
        self.reference = self.root / "EP007/edit/editlist.json"
        self.reference.write_text(json.dumps({"segments": [
            {"name": "07", "src": "video/v1/shot07_fix.mp4"}]}), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def manifest(self, **item_overrides):
        item = {"path": "EP007/video/v1/shot07.mp4", "shot_id": "07",
                "status": "superseded", "sha256": gc.digest(self.rejected),
                "reason": "identity mismatch", "evidence": "EP007/edit/QC_REPORT.md"}
        item.update(item_overrides)
        return {"version": 1, "project_root": str(self.root),
                "generated_roots": ["EP007/video/v1"],
                "reference_files": ["EP007/edit/editlist.json"],
                "retained": [{"path": "EP007/video/v1/shot07_fix.mp4", "shot_id": "07"}],
                "items": [item]}

    def test_dry_run_plans_without_touching_media(self):
        report, _, _ = gc.plan(self.manifest())
        self.assertEqual(report["summary"]["planned"], 1)
        self.assertEqual(report["summary"]["bytes_reclaimable"], len(b"rejected"))
        self.assertTrue(self.rejected.exists())

    def test_execute_deletes_only_the_reviewed_candidate(self):
        report, root, archive = gc.plan(self.manifest())
        gc.execute(report, root, archive, "delete")
        self.assertFalse(self.rejected.exists())
        self.assertTrue(self.accepted.exists())
        self.assertEqual(report["actions"][0]["status"], "deleted")

    def test_editlist_reference_blocks_deletion(self):
        data = json.loads(self.reference.read_text(encoding="utf-8"))
        data["segments"].append({"name": "old", "src": "video/v1/shot07.mp4"})
        self.reference.write_text(json.dumps(data), encoding="utf-8")
        report, _, _ = gc.plan(self.manifest())
        self.assertEqual(report["actions"][0]["code"], "STILL_REFERENCED")
        self.assertTrue(self.rejected.exists())

    def test_changed_hash_blocks_deletion(self):
        manifest = self.manifest()
        self.rejected.write_bytes(b"changed after review")
        old = time.time() - 3 * 86400
        os.utime(self.rejected, (old, old))
        report, _, _ = gc.plan(manifest)
        self.assertEqual(report["actions"][0]["code"], "FILE_CHANGED_SINCE_REVIEW")

    def test_missing_fallback_blocks_deletion(self):
        manifest = self.manifest()
        manifest["retained"] = []
        report, _, _ = gc.plan(manifest)
        self.assertEqual(report["actions"][0]["code"], "NO_RETAINED_FALLBACK")

    def test_blocked_item_prevents_entire_execution(self):
        manifest = self.manifest(sha256="0" * 64)
        report, root, archive = gc.plan(manifest)
        with self.assertRaises(ValueError):
            gc.execute(report, root, archive, "delete")
        self.assertTrue(self.rejected.exists())
        self.assertTrue(self.accepted.exists())

    def test_retained_file_cannot_be_a_cleanup_item(self):
        self.reference.write_text(json.dumps({"segments": []}), encoding="utf-8")
        old = time.time() - 3 * 86400
        os.utime(self.accepted, (old, old))
        manifest = self.manifest(path="EP007/video/v1/shot07_fix.mp4",
                                 sha256=gc.digest(self.accepted), status="rejected")
        report, _, _ = gc.plan(manifest)
        self.assertEqual(report["actions"][0]["code"], "RETAINED_FALLBACK")

    def test_recent_unreviewed_or_outside_files_are_protected(self):
        recent = self.generated / "shot08.mp4"
        recent.write_bytes(b"recent")
        manifest = self.manifest(path="EP007/video/v1/shot08.mp4", shot_id="08",
                                 status="rejected", sha256=gc.digest(recent))
        manifest["retained"].append({"path": "EP007/video/v1/shot07_fix.mp4", "shot_id": "08"})
        report, _, _ = gc.plan(manifest)
        self.assertEqual(report["actions"][0]["code"], "TOO_RECENT")
        report, _, _ = gc.plan(self.manifest(path="EP007/assets/ref.png", orphan_allowed=True))
        self.assertEqual(report["actions"][0]["code"], "OUTSIDE_GENERATED_ROOTS")


if __name__ == "__main__":
    unittest.main()
