from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "submission_gateway", ROOT / "skills/produce-ai-video/scripts/submission_gateway.py")
gateway = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gateway)
ledger = gateway.ledger


class SubmissionGatewayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.state_path = self.root / "state.json"
        self.record_path = self.root / "submission.json"
        self.evidence = self.root / "review.txt"
        self.evidence.write_text("Synthetic fixture; not a real semantic/media review.")
        self.image = self.root / "frame.png"
        self.image.write_bytes(b"synthetic frame")
        self.prefix = "aifilm/sc01_s1_s0"
        ledger.apply(self.state_path, {"action": "init"})
        self.put("location", "asset", data={"kind": "scene"})
        self.put("director", "director", data={"fixture": "shot package"})
        self.put("frame", "keyframe", path=self.image, dependencies=["location", "director"])
        self.graph = {
            "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "fixture-model"}},
            "20": {"class_type": "MiniMaxH3TimelineDirector", "inputs": {
                "prompt": "<Picture 1> The empty room remains still.",
                "generation_seconds": 5,
                "timeline_data": json.dumps({
                    "images": [{"file": self.image.name}], "audios": [], "videoClips": [],
                }),
            }},
            "29": {"class_type": "SaveVideo", "inputs": {"filename_prefix": self.prefix}},
        }
        actual = gateway.describe(self.graph, self.root)
        sha = ledger.file_hash(self.image)
        self.record = {
            "schema": "film-skills.runtime-submission/v1", "scope": "shot",
            "voice_assets": {},
            "prompt_preflight": {
                "schema": gateway.prompt_check.SCHEMA, "model": actual["model"],
                "parameters": {"graph_sha256": actual["request_sha256"]},
                "prompt": actual["prompt"],
                "compiler": {"name": None, "version": None, "status": "not_used",
                             "scope": "not_applicable", "source_prompt": actual["prompt"],
                             "fallback_reason": None, "additions": []},
                "locks": {"required": [], "forbidden": []},
                "asset_inventory": {"coverage": "complete", "assets": [{
                    "id": "location", "kind": "scene", "status": "approved",
                    "version": ledger.read_state(self.state_path)["artifacts"]["location"]["fingerprint"],
                    "evidence": "fixture-attestation",
                }]},
                "binding": {"scheme": "h3_explicit",
                            "max_by_kind": {"image": 9, "video": 1, "audio": 3},
                            "capacity_evidence": "fixture schema"},
                "attachments": [{
                    "kind": "image", "label": "<Picture 1>", "role": "composition_reference",
                    "path": str(self.image), "sha256": sha,
                    "review": {"status": "approved", "sha256": sha,
                               "evidence": "fixture-attestation"},
                }],
            },
            "shot_preflight": {
                "schema": gateway.shot_check.SCHEMA, "tracked_items": [], "shots": [{
                    "id": "sc01_s1_s0", "duration_seconds": 5,
                    "prompt": actual["prompt"], "audio_route": "silent", "dialogue": [],
                    "entry_state": {}, "exit_state": {},
                }],
            },
        }
        self.save_record()

    def put(self, aid, kind, path=None, data=None, dependencies=()):
        ledger.apply(self.state_path, {
            "action": "register", "id": aid, "kind": kind,
            "path": str(path) if path else None, "data": data or {},
            "dependencies": list(dependencies),
        })
        for domain in ledger.DOMAINS[kind]:
            ledger.apply(self.state_path, {
                "action": "review", "id": aid, "domain": domain, "verdict": "accepted",
                "authority": "delegated", "reviewer": "fixture",
                "evidence": str(self.evidence),
            })

    def save_record(self, extra=()):
        self.record_path.write_text(json.dumps(self.record))
        self.put("submission:sc01_s1_s0", "submission", path=self.record_path,
                 data={"request_sha256": gateway.describe(
                     self.graph, self.root)["request_sha256"]},
                 dependencies=["location", "director", "frame", *extra])

    def check(self, graph=None):
        return gateway.checked(self.state_path, self.record_path,
                               graph or self.graph, self.root, self.prefix)

    def test_reviewed_fixture_reserves_and_uses_content_addressed_inputs(self):
        ticket = gateway.prepare(self.state_path, self.record_path, self.graph,
                                 self.root, self.prefix)
        timeline = json.loads(ticket["graph"]["20"]["inputs"]["timeline_data"])
        snapshot = self.root / timeline["images"][0]["file"]
        self.assertEqual(snapshot.read_bytes(), self.image.read_bytes())
        self.assertEqual(snapshot.parent.name, ".film-gate")
        self.assertEqual(ledger.digest(ticket["graph"]), ticket["request_sha256"])
        self.assertNotEqual(ticket["graph"], self.graph)
        with self.assertRaises(ValueError):
            gateway.prepare(self.state_path, self.record_path, self.graph, self.root, self.prefix)

    def test_changed_graph_cannot_reuse_reviews(self):
        changed = copy.deepcopy(self.graph)
        changed["1"]["inputs"]["unet_name"] = "different-model"
        with self.assertRaisesRegex(ValueError, "actual graph changed"):
            self.check(changed)

    def test_changed_same_filename_and_changed_record_are_blocked(self):
        self.image.write_bytes(b"different frame")
        with self.assertRaises(ValueError):
            self.check()
        self.image.write_bytes(b"synthetic frame")
        self.record_path.write_text("{}")
        with self.assertRaises(ValueError):
            self.check()

    def test_full_film_needs_screenplay_and_animatic_not_just_a_shot(self):
        self.record["scope"] = "film"
        self.save_record()
        with self.assertRaisesRegex(ValueError, "upstream production stages"):
            self.check()

    def test_calling_reference_a_hard_first_frame_is_blocked(self):
        self.record["prompt_preflight"]["attachments"][0]["role"] = "opening_frame"
        self.save_record()
        with self.assertRaisesRegex(ValueError, "not hard first-frame"):
            self.check()

    def test_shot_check_must_cover_the_same_actual_prompt(self):
        self.record["shot_preflight"]["shots"][0]["prompt"] = "Another scene."
        self.save_record()
        with self.assertRaisesRegex(ValueError, "different text"):
            self.check()

    def test_native_dialogue_without_actual_voice_reference_is_blocked(self):
        shot = self.record["shot_preflight"]["shots"][0]
        shot.update(audio_route="native", dialogue=[{"speaker": "Actor", "text": "hello"}],
                    speech_timing={"measured_seconds": 1, "window_seconds": 5,
                                   "basis": "fixture timed take", "cross_shot": False})
        prompt = "<Picture 1> The actor says hello."
        self.graph["20"]["inputs"]["prompt"] = prompt
        record = self.record["prompt_preflight"]
        record.update(prompt=prompt)
        record["compiler"]["source_prompt"] = prompt
        record["parameters"]["graph_sha256"] = gateway.describe(
            self.graph, self.root)["request_sha256"]
        shot["prompt"] = prompt
        self.save_record()
        with self.assertRaisesRegex(ValueError, "voice reference"):
            self.check()

    def test_empty_voice_mapping_does_not_authorize_missing_audio(self):
        self.record["prompt_preflight"]["asset_inventory"]["coverage"] = "unverified"
        self.save_record()
        with self.assertRaisesRegex(ValueError, "unknown preflight"):
            self.check()

    def test_native_guide_binding_requires_explicit_review_resolution(self):
        self.record["prompt_preflight"]["binding"]["scheme"] = "opaque"
        self.save_record()
        with self.assertRaisesRegex(ValueError, "versioned evidence"):
            self.check()
        findings = gateway.prompt_check.audit(self.record["prompt_preflight"])["findings"]
        self.record["resolved_findings"] = [
            {"checker": "prompt", "finding_sha256": ledger.digest(finding),
             "evidence_id": "director"} for finding in findings]
        self.save_record()
        self.check()
        self.record["resolved_findings"][0]["finding_sha256"] = "0" * 64
        self.save_record()
        with self.assertRaises(ValueError):
            self.check()

    def test_path_traversal_and_corrupted_snapshots_are_blocked(self):
        graph = copy.deepcopy(self.graph)
        graph["20"]["inputs"]["timeline_data"] = json.dumps({
            "images": [{"file": "../outside.png"}]})
        with self.assertRaisesRegex(ValueError, "escapes"):
            gateway.describe(graph, self.root)
        actual = gateway.describe(self.graph, self.root)
        gateway.snapshots(actual["files"])
        Path(actual["files"][0]["snapshot"]).write_bytes(b"corrupted")
        with self.assertRaisesRegex(ValueError, "snapshot was changed"):
            gateway.snapshots(actual["files"])

    def _continuation_fixture(self, timeline_extra=None):
        previous = self.root / "prev.mp4"
        previous.write_bytes(b"synthetic previous clip")
        self.put("prev", "video", path=previous)
        prompt = ("<Picture 1> The empty room remains still. <Video 1> continues the motion. "
                  "<Audio 1> is the original room tone.")
        timeline = {
            "images": [{"file": self.image.name}], "audios": [],
            "videoClips": [{"id": "clip-1", "file": previous.name, "name": previous.name,
                            "start": 0.0, "duration": 5.0, "referenceMode": "guide"}],
            "selection": {"start": 4.7, "duration": 5.0},
        }
        timeline.update(timeline_extra or {})
        self.graph["20"]["inputs"]["prompt"] = prompt
        self.graph["20"]["inputs"]["timeline_data"] = json.dumps(timeline)
        return previous, prompt

    def _declare_continuation(self, prompt, actual):
        prompt_record = self.record["prompt_preflight"]
        prompt_record.update(prompt=prompt)
        prompt_record["compiler"]["source_prompt"] = prompt
        prompt_record["parameters"]["graph_sha256"] = actual["request_sha256"]
        prompt_record["attachments"] = [{
            "kind": item["kind"], "label": item["label"],
            "role": "composition_reference" if item["kind"] == "image" else "continuation_guide",
            "path": item["path"], "sha256": item["sha256"],
            "review": {"status": "approved", "sha256": item["sha256"],
                       "evidence": "fixture-attestation"},
        } for item in actual["files"]]
        self.record["shot_preflight"]["shots"][0]["prompt"] = prompt

    def test_paired_previous_clip_audio_is_declared_and_cannot_be_omitted(self):
        self._continuation_fixture()
        actual = gateway.describe(self.graph, self.root)
        self.assertEqual([x["label"] for x in actual["files"]],
                         ["<Picture 1>", "<Video 1>", "<Audio 1>"])
        self.assertTrue(actual["files"][2]["derived"])
        self._declare_continuation(self.graph["20"]["inputs"]["prompt"], actual)
        self.save_record(extra=("prev",))
        self.check()
        omitted = copy.deepcopy(self.record)
        omitted["prompt_preflight"]["attachments"].pop()
        self.record = omitted
        self.save_record(extra=("prev",))
        with self.assertRaisesRegex(ValueError, "attachment order"):
            self.check()

    def test_unmodelled_timeline_media_is_refused_not_guessed(self):
        self._continuation_fixture({"audios": [{"file": self.image.name, "audioMode": "locked"}]})
        with self.assertRaisesRegex(ValueError, "locked"):
            gateway.describe(self.graph, self.root)
        self._continuation_fixture({"videoClips": [{
            "id": "clip-1", "file": "prev.mp4", "name": "prev.mp4", "start": 0.0,
            "duration": 5.0, "referenceMode": "boundary"}]})
        with self.assertRaisesRegex(ValueError, "guide-mode"):
            gateway.describe(self.graph, self.root)
        self._continuation_fixture({"selection": {"start": 0.0, "duration": 5.0},
                                    "videoClips": [{"id": "clip-1", "file": "prev.mp4",
                                                    "name": "prev.mp4", "start": 20.0,
                                                    "duration": 5.0, "referenceMode": "guide"}]})
        with self.assertRaisesRegex(ValueError, "outside the generated range"):
            gateway.describe(self.graph, self.root)

    def test_draft_has_explicit_unknowns_and_cannot_pass(self):
        draft = gateway.draft(self.graph, self.root, self.prefix)
        report = gateway.prompt_check.audit(draft["prompt_preflight"])
        self.assertTrue(report["findings"])
        self.assertEqual(draft["prompt_preflight"]["asset_inventory"]["coverage"], "unverified")
        self.assertEqual(draft["scope"], "film")

    def test_unknown_graph_nodes_and_wrong_output_slot_are_blocked(self):
        unknown = copy.deepcopy(self.graph)
        unknown["30"] = {"class_type": "LoadUnreviewedMedia", "inputs": {}}
        with self.assertRaisesRegex(ValueError, "unsupported graph"):
            gateway.describe(unknown, self.root)
        self.graph["29"]["inputs"]["filename_prefix"] = "another/output"
        self.record["prompt_preflight"]["parameters"]["graph_sha256"] = gateway.describe(
            self.graph, self.root)["request_sha256"]
        self.save_record()
        with self.assertRaisesRegex(ValueError, "output slot"):
            self.check()


if __name__ == "__main__":
    unittest.main()
