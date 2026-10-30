from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "skills/produce-ai-video/scripts/prompt_preflight.py"
SPEC = importlib.util.spec_from_file_location("prompt_preflight", CLI)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def attachment(path, label="<Picture 1>", kind="image"):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "kind": kind, "label": label, "role": "opening_frame",
        "path": str(path), "sha256": digest,
        "review": {"status": "approved", "sha256": digest, "evidence": "review-1"},
    }


def sample(path):
    prompt = ("<Picture 1> The examiner turns the deceased man's palm. "
              "Residue is visible on the fingertips.")
    return {
        "schema": checker.SCHEMA,
        "model": "h3-test-mode",
        "parameters": {"fps": 24, "frames": 90},
        "prompt": prompt,
        "compiler": {
            "name": "local-compiler", "version": "test-v1", "status": "completed",
            "scope": "restrained", "source_prompt": "Examine the deceased man's hand.",
            "fallback_reason": None, "additions": [],
        },
        "locks": {
            "required": ["turns the deceased man's palm", "Residue is visible"],
            "forbidden": ["the named facial detail fills the frame",
                          "The deceased man blinks"],
        },
        "asset_inventory": {
            "coverage": "complete",
            "assets": [{"id": "victim", "kind": "character", "status": "approved",
                        "version": "v1", "evidence": "character-review-1"}],
        },
        "binding": {"scheme": "h3_explicit", "max_by_kind": {"image": 9},
                    "capacity_evidence": "verified test runtime"},
        "attachments": [attachment(path)],
    }


def codes(result):
    return {item["code"] for item in result["findings"]}


class PromptPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.image = self.root / "frame.png"
        self.image.write_bytes(b"synthetic test image")
        self.data = sample(self.image)

    def test_clean_declarations_never_claim_semantic_or_visual_approval(self):
        result = checker.audit(self.data)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["semantic_review"], "not_performed")
        self.assertEqual(result["asset_review"], "not_performed")
        self.assertEqual(result["keyframe_visual_review"], "not_performed")
        self.assertFalse(result["actual_model_submission_checked"])
        self.assertEqual(result["attachments"][0]["actual_sha256"],
                         self.data["attachments"][0]["sha256"])
        self.assertIsNotNone(result["declared_payload_sha256"])

    def test_exact_hand_shot_locks_detect_declared_conflicts_and_missing_evidence(self):
        self.data["prompt"] += " The named facial detail fills the frame."
        # Literal locks are case-sensitive: record the actual conflicting fragment.
        self.data["locks"]["forbidden"][0] = "The named facial detail fills the frame"
        result = checker.audit(self.data)
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("FORBIDDEN_LITERAL_PRESENT", codes(result))
        self.data["prompt"] = self.data["prompt"].replace("Residue is visible", "A trace appears")
        self.assertIn("REQUIRED_LITERAL_MISSING", codes(checker.audit(self.data)))

    def test_a_living_operator_is_not_a_global_dead_body_prohibition(self):
        self.data["prompt"] += " The examiner blinks."
        self.assertNotIn("FORBIDDEN_LITERAL_PRESENT", codes(checker.audit(self.data)))
        self.data["prompt"] += " The deceased man blinks."
        self.assertIn("FORBIDDEN_LITERAL_PRESENT", codes(checker.audit(self.data)))

    def test_unrecorded_semantic_conflict_is_not_automatically_detected(self):
        self.data["locks"]["forbidden"] = []
        self.data["prompt"] += " The deceased man blinks."
        result = checker.audit(self.data)
        self.assertNotIn("FORBIDDEN_LITERAL_PRESENT", codes(result))
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["semantic_review"], "not_performed")

    def test_explicit_additions_require_authorization_and_exact_evidence(self):
        self.data["prompt"] += " A song begins."
        extra = {"kind": "music", "text": "A song begins.",
                 "authorization": "prohibited", "evidence": None}
        self.data["compiler"]["additions"] = [extra]
        self.assertIn("PROHIBITED_ADDITION", codes(checker.audit(self.data)))
        extra["authorization"] = "unverified"
        self.assertIn("ADDITION_AUTHORIZATION_UNVERIFIED", codes(checker.audit(self.data)))
        extra.update(authorization="authorized", evidence="approved-director-package")
        result = checker.audit(self.data)
        self.assertNotIn("ADDITION_AUTHORIZATION_UNVERIFIED", codes(result))
        extra["text"] = "A different song begins."
        self.assertIn("ADDITION_NOT_IN_PROMPT", codes(checker.audit(self.data)))

    def test_unrecorded_additions_cannot_be_proved_absent(self):
        self.data["prompt"] += " A song begins."
        result = checker.audit(self.data)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["semantic_review"], "not_performed")

    def test_fallback_and_unknown_scope_are_review_required(self):
        compiler = self.data["compiler"]
        compiler.update(status="fallback", fallback_reason=None, scope="unverified")
        result = checker.audit(self.data)
        self.assertTrue({"COMPILER_RESULT_UNVERIFIED", "FALLBACK_REASON_MISSING",
                         "ENHANCEMENT_SCOPE_UNVERIFIED"} <= codes(result))
        compiler["fallback_reason"] = "writer unavailable"
        self.assertNotIn("FALLBACK_REASON_MISSING", codes(checker.audit(self.data)))
        compiler.update(status="not_used", source_prompt="different text")
        self.assertIn("COMPILER_STATUS_MISMATCH", codes(checker.audit(self.data)))

    def test_missing_or_unverified_declared_assets_are_not_approved(self):
        assets = self.data["asset_inventory"]["assets"]
        assets.append({"id": "female-victim", "kind": "character", "status": "missing",
                       "version": None, "evidence": None})
        result = checker.audit(self.data)
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("REQUIRED_ASSET_NOT_APPROVED", codes(result))
        assets[-1]["status"] = "unverified"
        self.assertIn("REQUIRED_ASSET_UNVERIFIED", codes(checker.audit(self.data)))
        assets[-1].update(status="approved", version="v2", evidence=None)
        self.assertIn("REQUIRED_ASSET_UNVERIFIED", codes(checker.audit(self.data)))
        self.data["asset_inventory"]["coverage"] = "incomplete"
        self.assertIn("ASSET_INVENTORY_INCOMPLETE", codes(checker.audit(self.data)))

    def test_no_recorded_characters_does_not_prove_no_characters_are_required(self):
        self.data["asset_inventory"]["assets"] = []
        self.data["prompt"] += " A man and woman lie in the car."
        result = checker.audit(self.data)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["asset_review"], "not_performed")

    def test_h3_reference_errors_are_not_silently_repaired(self):
        self.data["prompt"] += " <Picture 2>"
        self.assertIn("REFERENCE_LABEL_UNBOUND", codes(checker.audit(self.data)))
        self.data["prompt"] = self.data["prompt"].replace("<Picture 2>", "<Image 2>")
        self.assertIn("REFERENCE_LABEL_MALFORMED", codes(checker.audit(self.data)))
        self.data["attachments"][0]["label"] = "<Audio 1>"
        self.assertIn("REFERENCE_KIND_MISMATCH", codes(checker.audit(self.data)))

    def test_reference_numbering_and_duplicate_labels_follow_attachment_order(self):
        second = self.root / "second.png"
        second.write_bytes(b"another synthetic image")
        self.data["attachments"].append(attachment(second, "<Picture 2>"))
        self.data["prompt"] += " <Picture 2>"
        self.assertEqual(checker.audit(self.data)["findings"], [])
        self.data["attachments"].reverse()
        self.assertIn("REFERENCE_ORDER_MISMATCH", codes(checker.audit(self.data)))
        self.data["attachments"][0]["label"] = "<Picture 1>"
        self.assertIn("REFERENCE_LABEL_DUPLICATE", codes(checker.audit(self.data)))

    def test_unused_labels_and_opaque_adapter_require_review(self):
        second = self.root / "second.png"
        second.write_bytes(b"another synthetic image")
        self.data["attachments"].append(attachment(second, "<Picture 2>"))
        self.assertIn("REFERENCE_LABEL_UNUSED", codes(checker.audit(self.data)))
        self.data["binding"]["scheme"] = "opaque"
        self.assertIn("REFERENCE_BINDING_OPAQUE", codes(checker.audit(self.data)))

    def test_reference_capacity_is_checked_without_truncation(self):
        second = self.root / "second.png"
        second.write_bytes(b"another synthetic image")
        self.data["attachments"].append(attachment(second, "<Picture 2>"))
        self.data["prompt"] += " <Picture 2>"
        self.data["binding"]["max_by_kind"]["image"] = 1
        self.assertIn("REFERENCE_CAPACITY_EXCEEDED", codes(checker.audit(self.data)))
        self.data["binding"]["max_by_kind"] = {}
        self.assertIn("REFERENCE_CAPACITY_UNVERIFIED", codes(checker.audit(self.data)))

    def test_changed_file_or_wrong_approval_hash_blocks(self):
        self.image.write_bytes(b"changed after approval")
        result = checker.audit(self.data)
        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue({"ATTACHMENT_HASH_MISMATCH", "ATTACHMENT_REVIEW_HASH_MISMATCH"}
                        <= codes(result))
        updated = hashlib.sha256(self.image.read_bytes()).hexdigest()
        self.data["attachments"][0]["sha256"] = updated
        self.assertIn("ATTACHMENT_REVIEW_HASH_MISMATCH", codes(checker.audit(self.data)))
        self.data["attachments"][0]["review"]["sha256"] = updated
        self.assertEqual(checker.audit(self.data)["findings"], [])

    def test_missing_file_review_and_expected_hash_remain_unverified(self):
        ref = self.data["attachments"][0]
        ref.update(path=None, sha256=None)
        ref["review"] = {"status": "unverified", "sha256": None, "evidence": None}
        result = checker.audit(self.data)
        self.assertTrue({"ATTACHMENT_FILE_UNVERIFIED", "ATTACHMENT_EXPECTED_HASH_UNVERIFIED",
                         "ATTACHMENT_REVIEW_UNVERIFIED"} <= codes(result))
        self.assertIsNone(result["declared_payload_sha256"])
        ref["review"]["status"] = "rejected"
        self.assertEqual(checker.audit(self.data)["status"], "BLOCK")

    def test_directory_and_oversized_files_are_not_read_as_valid_attachments(self):
        self.data["attachments"][0]["path"] = str(self.root)
        self.assertIn("ATTACHMENT_FILE_UNVERIFIED", codes(checker.audit(self.data)))
        self.data["attachments"][0]["path"] = str(self.image)
        with mock.patch.object(checker, "MAX_ATTACHMENT_BYTES", 3):
            self.assertIn("ATTACHMENT_FILE_UNVERIFIED", codes(checker.audit(self.data)))

    @unittest.skipUnless(hasattr(os, "mkfifo"), "requires a named pipe")
    def test_named_pipe_is_not_read_or_blocked(self):
        pipe = self.root / "pipe"
        os.mkfifo(pipe)
        self.data["attachments"][0]["path"] = str(pipe)
        self.assertIn("ATTACHMENT_FILE_UNVERIFIED", codes(checker.audit(self.data)))

    def test_hash_binds_prompt_model_parameters_and_attachment_bytes(self):
        original = checker.audit(self.data)
        for edit in (
            lambda x: x.update(prompt=x["prompt"] + " A light changes."),
            lambda x: x.update(model="another-model"),
            lambda x: x["parameters"].update(frames=107),
            lambda x: x["attachments"][0].update(role="style_reference"),
        ):
            changed = copy.deepcopy(self.data)
            edit(changed)
            self.assertNotEqual(original["declared_payload_sha256"],
                                checker.audit(changed)["declared_payload_sha256"])
        changed = copy.deepcopy(self.data)
        changed["compiler"]["source_prompt"] += " Original direction changes."
        result = checker.audit(changed)
        self.assertNotEqual(original["source_prompt_sha256"], result["source_prompt_sha256"])
        self.assertEqual(original["declared_payload_sha256"], result["declared_payload_sha256"])

    def test_invalid_structures_and_relative_paths_are_rejected(self):
        for edit in (
            lambda x: x.update(unexpected=True),
            lambda x: x["attachments"][0].update(path="relative.png"),
            lambda x: x["attachments"][0].update(sha256="not-a-hash"),
            lambda x: x["binding"]["max_by_kind"].update(image=True),
            lambda x: x["compiler"].update(scope="unknown-choice"),
            lambda x: x["parameters"].update(fps=float("nan")),
        ):
            data = copy.deepcopy(self.data)
            edit(data)
            with self.assertRaises(checker.InputError):
                checker.audit(data)

    def test_cli_reports_hashes_but_not_the_prompt_and_requires_review(self):
        path = self.root / "request.json"
        path.write_text(json.dumps(self.data), encoding="utf-8")
        command = [sys.executable, "-B", str(CLI), "--input", str(path)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertNotIn(self.data["prompt"], result.stdout)
        self.assertEqual(report["input_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

        self.data["prompt"] += " <Picture 2>"
        path.write_text(json.dumps(self.data), encoding="utf-8")
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["status"], "BLOCK")

    def test_cli_rejects_duplicate_keys_and_nonfinite_numbers(self):
        path = self.root / "bad.json"
        command = [sys.executable, "-B", str(CLI), "--input", str(path)]
        for content in ('{"schema": "x", "schema": "y"}', '{"value": NaN}'):
            path.write_text(content, encoding="utf-8")
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)["status"], "INVALID_INPUT")

    def test_chinese_locked_lines_use_exact_unicode_text(self):
        line = "\u628a\u7269\u8bc1\u76d2\u4ea4\u7ed9\u6211\u3002"
        self.data["prompt"] += " " + line
        self.data["locks"]["required"].append(line)
        self.assertNotIn("REQUIRED_LITERAL_MISSING", codes(checker.audit(self.data)))
        self.data["prompt"] = self.data["prompt"].replace(line, line[:-1])
        self.assertIn("REQUIRED_LITERAL_MISSING", codes(checker.audit(self.data)))

    def test_documented_example_is_valid_after_replacing_placeholders(self):
        path = ROOT / "skills/produce-ai-video/references/prompt-compilation-preflight.md"
        example = path.read_text(encoding="utf-8").split("```json\n", 1)[1].split("\n```", 1)[0]
        data = json.loads(example)
        data["attachments"][0] = attachment(self.image)
        result = checker.audit(data)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["findings"], [])

    def test_context_ir_prompt_runs_structural_check(self):
        audio = self.root / "voice.wav"
        audio.write_bytes(b"synthetic test audio")
        self.data["attachments"].append(attachment(audio, "<Audio 1>", "audio"))
        self.data["binding"]["max_by_kind"]["audio"] = 4
        self.data["prompt_format"] = "context_ir"
        self.data["prompt"] = (
            "subject_definitions:\n"
            "<Subject 1> is the examiner in <Picture 1>.\n"
            "<Picture 1> is the first frame of [Shot 1].\n"
            "<Audio 1> is the voice-timbre reference for <Subject 1> (S1).\n\n"
            "summary:\n"
            "[reference generation + audio reference] <Subject 1> speaks.\n\n"
            "retention_analysis:\n"
            "<Subject 1>: fully_preserved - identity retained.\n"
            "<Picture 1>: fully_preserved - opening frame retained.\n"
            "<Audio 1>: reference - timbre only.\n\n"
            "detailed_description:\n"
            "[Shot 1] <Subject 1> (S1) at the <Picture 1> framing says, "
            "<d>[Mandarin] 会议开始。</d>\n\n"
            "overall_soundscape:\nRoom tone.\n\nnon_diegetic_music:\nN/A\n")
        self.data["locks"] = {"required": ["会议开始"], "forbidden": []}
        result = checker.audit(self.data)
        self.assertEqual(result["context_ir_structure"], "checked")
        self.assertEqual(result["findings"], [])
        bad = copy.deepcopy(self.data)
        bad["prompt"] = bad["prompt"].replace("retention_analysis:", "notes:")
        result = checker.audit(bad)
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("SECTION_STRUCTURE", codes(result))
        bad["prompt_format"] = "unknown_format"
        with self.assertRaises(checker.InputError):
            checker.audit(bad)

    def test_h3_base_prompt_runs_structural_check(self):
        self.data["prompt_format"] = "h3_base"
        self.data["h3_mode"] = "i2va"
        self.data["prompt"] = (
            "For the target video, at 0.00 seconds into the target video, "
            "<Picture 1> (from [Shot 1]) is fully referenced.\n\n"
            "integrated_multimodal_description: [Shot 1] The woman in "
            "<Picture 1> turns to the window and says, "
            "<d>[English] I get off at the next station.</d>\n\n"
            "overall_soundscape: A steady wheel rhythm.\n\n"
            "non_diegetic_music: N/A\n")
        self.data["locks"] = {"required": ["turns to the window"], "forbidden": []}
        result = checker.audit(self.data)
        self.assertEqual(result["h3_base_structure"], "checked")
        self.assertEqual(result["findings"], [])
        bad = copy.deepcopy(self.data)
        del bad["h3_mode"]
        result = checker.audit(bad)
        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("H3_BASE_MODE_UNDECLARED", codes(result))
        bad = copy.deepcopy(self.data)
        bad["prompt"] = bad["prompt"].replace("overall_soundscape:", "notes:")
        result = checker.audit(bad)
        self.assertIn("FIELD_STRUCTURE", codes(result))

    def test_shot_and_prompt_reports_can_be_bound_to_the_same_text(self):
        shot_cli = ROOT / "skills/produce-ai-video/scripts/shot_preflight.py"
        shot_spec = importlib.util.spec_from_file_location("shot_checker", shot_cli)
        shot = importlib.util.module_from_spec(shot_spec)
        shot_spec.loader.exec_module(shot)
        shot_data = {
            "schema": shot.SCHEMA,
            "tracked_items": [],
            "shots": [{"id": "S01", "duration_seconds": 4, "prompt": self.data["prompt"],
                       "audio_route": "silent", "dialogue": [],
                       "entry_state": {}, "exit_state": {}}],
        }
        shot_hash = shot.audit(shot_data)["prompts"][0]["prompt_sha256"]
        self.assertEqual(shot_hash, checker.audit(self.data)["prompt_sha256"])
        self.data["prompt"] += " A new detail."
        self.assertNotEqual(shot_hash, checker.audit(self.data)["prompt_sha256"])


if __name__ == "__main__":
    unittest.main()
