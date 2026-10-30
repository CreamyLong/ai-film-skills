from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "production_state", ROOT / "skills/produce-ai-video/scripts/production_state.py")
ledger = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ledger)


class ProductionStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "state.json"
        self.evidence = self.root / "review.txt"
        self.evidence.write_text("Synthetic test attestation, not a real media review.")
        ledger.apply(self.path, {"action": "init"})

    def register(self, aid, kind="asset", dependencies=(), path=None, data=None):
        return ledger.apply(self.path, {
            "action": "register", "id": aid, "kind": kind,
            "dependencies": list(dependencies), "path": str(path) if path else None,
            "data": data or {"fixture": aid},
        })

    def approve(self, aid):
        item = ledger.read_state(self.path)["artifacts"][aid]
        for domain in ledger.DOMAINS[item["kind"]]:
            ledger.apply(self.path, {
                "action": "review", "id": aid, "domain": domain, "verdict": "accepted",
                "authority": "delegated", "reviewer": "test-fixture",
                "evidence": str(self.evidence),
            })

    def ready(self, aid):
        return not ledger.problems(ledger.read_state(self.path), aid)

    def submission(self):
        request = ledger.digest({"test": "graph"})
        self.register("submit", kind="submission", data={"request_sha256": request})
        self.approve("submit")
        return request

    def receipt(self, attempt, status, provider_id="job-1"):
        receipt = self.root / f"{attempt}-{status}.json"
        receipt.write_text(json.dumps({"job_id": provider_id, "status": status}))
        return ledger.apply(self.path, {
            "action": "receipt", "attempt": attempt, "status": status,
            "provider_job_id": provider_id, "path": str(receipt),
        })

    def test_initialization_never_overwrites_and_missing_state_never_passes(self):
        original = self.path.read_bytes()
        with self.assertRaises(ledger.StateError):
            ledger.apply(self.path, {"action": "init"})
        self.assertEqual(self.path.read_bytes(), original)
        with self.assertRaises(FileNotFoundError):
            ledger.apply(self.root / "missing.json", {"action": "status"})

    def test_registration_does_not_imply_any_review(self):
        self.register("asset")
        self.assertFalse(self.ready("asset"))
        self.approve("asset")
        self.assertTrue(self.ready("asset"))

    def test_transitive_invalidation_preserves_unrelated_items_and_media(self):
        asset = self.root / "asset.png"
        asset.write_bytes(b"original")
        self.register("asset", path=asset)
        self.approve("asset")
        self.register("frame", "keyframe", ["asset"], path=asset)
        self.approve("frame")
        self.register("video", "video", ["frame"], path=asset)
        self.approve("video")
        self.register("unrelated")
        self.approve("unrelated")
        asset.write_bytes(b"new-version")
        result = self.register("asset", path=asset)
        self.assertEqual(result["invalidated"], ["frame", "video"])
        self.assertFalse(self.ready("video"))
        self.assertTrue(self.ready("unrelated"))
        self.assertEqual(asset.read_bytes(), b"new-version")
        self.assertTrue(ledger.read_state(self.path)["events"])

    def test_unchanged_registration_keeps_reviews(self):
        self.register("asset")
        self.approve("asset")
        self.assertFalse(self.register("asset")["changed"])
        self.assertTrue(self.ready("asset"))

    def test_changed_files_and_changed_review_evidence_are_not_reusable(self):
        asset = self.root / "asset.png"
        asset.write_bytes(b"version-one")
        self.register("asset", path=asset)
        self.approve("asset")
        asset.write_bytes(b"version-two")
        self.assertFalse(self.ready("asset"))
        self.register("asset", path=asset)
        self.approve("asset")
        self.evidence.write_text("Changed review")
        self.assertFalse(self.ready("asset"))

    def test_dependency_cycle_and_accepting_unready_dependencies_fail(self):
        self.register("a")
        self.register("b", dependencies=["a"])
        with self.assertRaises(ledger.StateError):
            self.approve("b")
        with self.assertRaises(ledger.StateError):
            self.register("a", dependencies=["b"])

    def test_another_writer_lock_is_not_removed(self):
        lock = self.path.with_name(self.path.name + ".lock")
        lock.write_text("another writer")
        with self.assertRaises(ledger.StateError):
            ledger.apply(self.path, {"action": "status"})
        self.assertTrue(lock.exists())

    def test_unknown_submission_is_not_blindly_retried(self):
        request = self.submission()
        command = {"action": "reserve", "id": "submit", "request_sha256": request}
        attempt = ledger.apply(self.path, command)["attempt"]
        self.receipt(attempt, "unknown", None)
        with self.assertRaises(ledger.StateError):
            ledger.apply(self.path, command)
        self.receipt(attempt, "submitted")
        self.receipt(attempt, "completed")
        with self.assertRaises(ledger.StateError):
            ledger.apply(self.path, command)

    def test_result_binding_requires_correct_job_and_does_not_approve_media(self):
        request = self.submission()
        attempt = ledger.apply(self.path, {
            "action": "reserve", "id": "submit", "request_sha256": request,
        })["attempt"]
        self.receipt(attempt, "submitted")
        self.receipt(attempt, "completed")
        media = self.root / "result.mp4"
        media.write_bytes(b"synthetic media")
        command = {"action": "bind", "attempt": attempt, "provider_job_id": "wrong",
                   "id": "result", "path": str(media)}
        with self.assertRaises(ledger.StateError):
            ledger.apply(self.path, command)
        command["provider_job_id"] = "job-1"
        result = ledger.apply(self.path, command)
        self.assertTrue(result["media_review_required"])
        self.assertFalse(self.ready("result"))

    def test_failed_job_can_retry_but_cannot_change_provider_identity(self):
        request = self.submission()
        command = {"action": "reserve", "id": "submit", "request_sha256": request}
        attempt = ledger.apply(self.path, command)["attempt"]
        self.receipt(attempt, "submitted")
        with self.assertRaises(ledger.StateError):
            self.receipt(attempt, "completed", "different-job")
        self.receipt(attempt, "failed")
        self.assertNotEqual(attempt, ledger.apply(self.path, command)["attempt"])

    def test_media_artifacts_cannot_be_approved_without_real_files(self):
        with self.assertRaisesRegex(ValueError, "actual local file"):
            self.register("film", kind="film")


if __name__ == "__main__":
    unittest.main()
