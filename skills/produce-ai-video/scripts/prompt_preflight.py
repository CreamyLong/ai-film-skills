#!/usr/bin/env python3
"""Check declared prompt compilation and local reference bindings without a model."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

SCHEMA = "film-skills.prompt-preflight/v1"
MAX_INPUT_BYTES = 2_000_000
MAX_ATTACHMENT_BYTES = 512 * 1024 * 1024
MAX_ATTACHMENTS = 32
SHA256 = re.compile(r"^[0-9a-f]{64}$")
H3_LABEL = re.compile(r"<(Picture|Video|Audio) ([1-9][0-9]*)>")
H3_LABEL_LIKE = re.compile(r"<\s*(?:picture|image|video|audio)\s*[0-9]+\s*>", re.I)
LABEL_KIND = {"Picture": "image", "Video": "video", "Audio": "audio"}
KINDS = ("image", "video", "audio", "other")


class InputError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise InputError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def nullable_text(value):
    return value is None or text(value)


def digest_value(value):
    return value is None or isinstance(value, str) and bool(SHA256.fullmatch(value))


def object_fields(value, allowed, required, location):
    require(isinstance(value, dict), f"{location}: expected object")
    require(set(value) <= allowed and required <= set(value), f"{location}: invalid fields")


def unique_json(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def sha256_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def file_fingerprint(path):
    """Hash only a stable, regular local file; do not read devices or named pipes."""
    if path is None:
        return None, "path unavailable"
    try:
        flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as handle:
            before = os.fstat(handle.fileno())
            if not stat.S_ISREG(before.st_mode):
                return None, "not a regular file"
            if before.st_size > MAX_ATTACHMENT_BYTES:
                return None, "file exceeds the local hashing limit"
            digest = hashlib.sha256()
            total = 0
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_ATTACHMENT_BYTES:
                    return None, "file exceeds the local hashing limit"
                digest.update(chunk)
            after = os.fstat(handle.fileno())
            current = os.stat(path)
            signature = lambda value: (value.st_dev, value.st_ino, value.st_size,
                                       value.st_mtime_ns)
            if signature(before) != signature(after) or signature(after) != signature(current):
                return None, "file changed while hashing"
            return digest.hexdigest(), None
    except (OSError, ValueError):
        return None, "file cannot be read"


def audit(data):
    root_fields = {"schema", "model", "parameters", "prompt", "compiler", "locks",
                   "asset_inventory", "binding", "attachments"}
    object_fields(data, root_fields, root_fields, "root")
    require(data["schema"] == SCHEMA, "unsupported schema")
    require(text(data["model"]), "/model: expected nonempty text")
    require(isinstance(data["parameters"], dict), "/parameters: expected object")
    require(text(data["prompt"]), "/prompt: expected nonempty text")
    try:
        json.dumps(data["parameters"], sort_keys=True, allow_nan=False)
    except (TypeError, ValueError, OverflowError, RecursionError):
        raise InputError("/parameters: expected finite JSON values") from None

    findings = []

    def add(code, severity, location, direction):
        findings.append({"code": code, "severity": severity, "location": location,
                         "repair_direction": direction})

    compiler = data["compiler"]
    compiler_fields = {"name", "version", "status", "scope", "source_prompt",
                       "fallback_reason", "additions"}
    object_fields(compiler, compiler_fields, compiler_fields, "/compiler")
    require(nullable_text(compiler["name"]) and nullable_text(compiler["version"]),
            "/compiler: invalid name or version")
    require(compiler["status"] in ("completed", "fallback", "unverified", "not_used"),
            "/compiler: invalid status")
    require(compiler["scope"] in ("restrained", "balanced", "bold", "extreme",
                                  "not_applicable", "unverified"),
            "/compiler: invalid scope")
    require(text(compiler["source_prompt"]) and nullable_text(compiler["fallback_reason"]),
            "/compiler: invalid source prompt or fallback reason")
    if compiler["status"] == "not_used" and compiler["source_prompt"] != data["prompt"]:
        add("COMPILER_STATUS_MISMATCH", "block", "/compiler/status",
            "Record the transformation actually used and recheck its output.")
    if compiler["status"] in ("fallback", "unverified"):
        add("COMPILER_RESULT_UNVERIFIED", "review", "/compiler/status",
            "Independently review the actual result or repair the compiler, then preflight again.")
    if compiler["status"] == "fallback" and compiler["fallback_reason"] is None:
        add("FALLBACK_REASON_MISSING", "review", "/compiler/fallback_reason",
            "Record why the compiler used a fallback.")
    if compiler["status"] != "not_used" and (
            compiler["name"] is None or compiler["version"] is None):
        add("COMPILER_VERSION_UNVERIFIED", "review", "/compiler",
            "Identify the compiler and its actual version.")
    if compiler["scope"] == "unverified":
        add("ENHANCEMENT_SCOPE_UNVERIFIED", "review", "/compiler/scope",
            "Establish which additions the directing package authorizes.")

    additions = compiler["additions"]
    require(isinstance(additions, list), "/compiler/additions: expected list")
    for index, addition in enumerate(additions):
        loc = f"/compiler/additions/{index}"
        fields = {"kind", "text", "authorization", "evidence"}
        object_fields(addition, fields, fields, loc)
        require(addition["kind"] in ("dialogue", "music", "on_screen_text", "performance",
                                     "action", "camera", "character", "prop",
                                     "environment", "other"), f"{loc}: invalid kind")
        require(text(addition["text"]) and nullable_text(addition["evidence"]),
                f"{loc}: invalid text or evidence")
        require(addition["authorization"] in ("authorized", "unverified", "prohibited"),
                f"{loc}: invalid authorization")
        if addition["text"] not in data["prompt"]:
            add("ADDITION_NOT_IN_PROMPT", "block", loc,
                "Reconcile the recorded addition with the exact submitted prompt.")
        if addition["authorization"] == "prohibited":
            add("PROHIBITED_ADDITION", "block", loc,
                "Remove the conflicting addition or obtain an authorized change to the source.")
        elif addition["authorization"] == "unverified" or addition["evidence"] is None:
            add("ADDITION_AUTHORIZATION_UNVERIFIED", "review", loc,
                "Verify this addition against the source and the user's authorization.")

    locks = data["locks"]
    object_fields(locks, {"required", "forbidden"}, {"required", "forbidden"}, "/locks")
    for kind in ("required", "forbidden"):
        values = locks[kind]
        require(isinstance(values, list) and all(text(x) for x in values)
                and len(values) == len(set(values)), f"/locks/{kind}: invalid list")
        for index, value in enumerate(values):
            present = value in data["prompt"]
            if kind == "required" and not present:
                add("REQUIRED_LITERAL_MISSING", "block", f"/locks/{kind}/{index}",
                    "Restore the locked text in the actual prompt or resolve the source conflict.")
            if kind == "forbidden" and present:
                add("FORBIDDEN_LITERAL_PRESENT", "block", f"/locks/{kind}/{index}",
                    "Remove or review the exact conflicting text before submission.")

    inventory = data["asset_inventory"]
    object_fields(inventory, {"coverage", "assets"}, {"coverage", "assets"},
                  "/asset_inventory")
    require(inventory["coverage"] in ("complete", "incomplete", "unverified"),
            "/asset_inventory: invalid coverage")
    require(isinstance(inventory["assets"], list), "/asset_inventory/assets: expected list")
    if inventory["coverage"] == "incomplete":
        add("ASSET_INVENTORY_INCOMPLETE", "block", "/asset_inventory/coverage",
            "Complete the required character, scene, prop and voice inventory.")
    elif inventory["coverage"] == "unverified":
        add("ASSET_INVENTORY_UNVERIFIED", "review", "/asset_inventory/coverage",
            "Compare the source and prompt with the actual asset inventory.")
    seen_assets = set()
    for index, asset in enumerate(inventory["assets"]):
        loc = f"/asset_inventory/assets/{index}"
        fields = {"id", "kind", "status", "version", "evidence"}
        object_fields(asset, fields, fields, loc)
        require(text(asset["id"]) and asset["id"] not in seen_assets, f"{loc}: invalid id")
        seen_assets.add(asset["id"])
        require(asset["kind"] in ("character", "scene", "prop", "voice", "other"),
                f"{loc}: invalid kind")
        require(asset["status"] in ("approved", "missing", "unverified", "rejected"),
                f"{loc}: invalid status")
        require(nullable_text(asset["version"]) and nullable_text(asset["evidence"]),
                f"{loc}: invalid version or evidence")
        if asset["status"] in ("missing", "rejected"):
            add("REQUIRED_ASSET_NOT_APPROVED", "block", loc,
                "Complete and approve this asset before dependent work.")
        elif asset["status"] == "unverified" or (
                asset["version"] is None or asset["evidence"] is None):
            add("REQUIRED_ASSET_UNVERIFIED", "review", loc,
                "Verify the current asset version and its approval record.")

    binding = data["binding"]
    fields = {"scheme", "max_by_kind", "capacity_evidence"}
    object_fields(binding, fields, fields, "/binding")
    require(binding["scheme"] in ("h3_explicit", "opaque"), "/binding: invalid scheme")
    limits = binding["max_by_kind"]
    require(isinstance(limits, dict) and set(limits) <= set(KINDS)
            and all(value is None or type(value) is int and value >= 0
                    for value in limits.values()), "/binding: invalid capacities")
    require(nullable_text(binding["capacity_evidence"]), "/binding: invalid evidence")
    attachments = data["attachments"]
    require(isinstance(attachments, list) and len(attachments) <= MAX_ATTACHMENTS,
            "/attachments: invalid list or too many files")
    if limits and binding["capacity_evidence"] is None:
        add("CAPACITY_EVIDENCE_UNVERIFIED", "review", "/binding/capacity_evidence",
            "Verify the limits for the actual model, mode and runtime.")
    for kind in KINDS:
        count = sum(isinstance(item, dict) and item.get("kind") == kind for item in attachments)
        limit = limits.get(kind)
        if count and limit is None:
            add("REFERENCE_CAPACITY_UNVERIFIED", "review", f"/binding/max_by_kind/{kind}",
                "Verify the attachment capacity; do not silently drop references.")
        elif limit is not None and count > limit:
            add("REFERENCE_CAPACITY_EXCEEDED", "block", f"/binding/max_by_kind/{kind}",
                "Choose an authorized compatible route or resolve the excess references.")

    declared_labels = set()
    next_number = {kind: 1 for kind in ("image", "video", "audio")}
    checked = []
    payload_attachments = []
    for index, attachment in enumerate(attachments):
        loc = f"/attachments/{index}"
        fields = {"kind", "label", "role", "path", "sha256", "review"}
        object_fields(attachment, fields, fields, loc)
        kind, label = attachment["kind"], attachment["label"]
        require(kind in KINDS and nullable_text(label) and text(attachment["role"]),
                f"{loc}: invalid kind, label or role")
        path = attachment["path"]
        require(path is None or text(path) and Path(path).is_absolute(),
                f"{loc}: path must be absolute or null")
        require(digest_value(attachment["sha256"]), f"{loc}: invalid sha256")
        review = attachment["review"]
        object_fields(review, {"status", "sha256", "evidence"},
                      {"status", "sha256", "evidence"}, f"{loc}/review")
        require(review["status"] in ("approved", "unverified", "rejected")
                and digest_value(review["sha256"]) and nullable_text(review["evidence"]),
                f"{loc}: invalid review")

        if binding["scheme"] == "h3_explicit":
            match = H3_LABEL.fullmatch(label or "")
            if kind == "other":
                add("REFERENCE_KIND_UNVERIFIED", "review", loc,
                    "Verify this attachment's binding against the actual runtime.")
            elif not match:
                add("REFERENCE_LABEL_MALFORMED", "block", f"{loc}/label",
                    "Use the exact H3 label for the actual media slot.")
            elif LABEL_KIND[match.group(1)] != kind:
                add("REFERENCE_KIND_MISMATCH", "block", f"{loc}/label",
                    "Match the label namespace to the attached media kind.")
            else:
                if label in declared_labels:
                    add("REFERENCE_LABEL_DUPLICATE", "block", f"{loc}/label",
                        "Assign a distinct label to each attachment slot.")
                declared_labels.add(label)
                if int(match.group(2)) != next_number[kind]:
                    add("REFERENCE_ORDER_MISMATCH", "block", f"{loc}/label",
                        "Match numbering to the runtime's actual per-kind attachment order.")
                next_number[kind] += 1

        actual, error = file_fingerprint(path)
        if error:
            add("ATTACHMENT_FILE_UNVERIFIED", "review", f"{loc}/path",
                f"Verify the actual local file: {error}.")
        if attachment["sha256"] is None:
            add("ATTACHMENT_EXPECTED_HASH_UNVERIFIED", "review", f"{loc}/sha256",
                "Record the expected content hash for this submitted attachment.")
        elif actual is not None and actual != attachment["sha256"]:
            add("ATTACHMENT_HASH_MISMATCH", "block", f"{loc}/sha256",
                "Use the intended file version and recheck the actual bytes.")
        if review["status"] == "rejected":
            add("ATTACHMENT_REJECTED", "block", f"{loc}/review",
                "Replace or repair the rejected reference and obtain a new review.")
        elif review["status"] == "unverified" or (
                review["sha256"] is None or review["evidence"] is None):
            add("ATTACHMENT_REVIEW_UNVERIFIED", "review", f"{loc}/review",
                "Verify the review record and its reviewed content hash.")
        if review["status"] == "approved" and review["sha256"] is not None:
            if actual is not None and actual != review["sha256"]:
                add("ATTACHMENT_REVIEW_HASH_MISMATCH", "block", f"{loc}/review/sha256",
                    "Review the exact file bytes that will be submitted.")
            elif attachment["sha256"] is not None and attachment["sha256"] != review["sha256"]:
                add("ATTACHMENT_REVIEW_HASH_MISMATCH", "block", f"{loc}/review/sha256",
                    "Reconcile the expected file and reviewed version.")
        checked.append({"index": index, "label": label, "actual_sha256": actual})
        payload_attachments.append({"kind": kind, "label": label, "role": attachment["role"],
                                    "sha256": actual})

    if binding["scheme"] == "h3_explicit":
        for match in H3_LABEL_LIKE.finditer(data["prompt"]):
            if not H3_LABEL.fullmatch(match.group()):
                add("REFERENCE_LABEL_MALFORMED", "block", "/prompt",
                    "Use the exact H3 label namespace and numbering.")
        used = {match.group() for match in H3_LABEL.finditer(data["prompt"])}
        if used - declared_labels:
            add("REFERENCE_LABEL_UNBOUND", "block", "/prompt",
                "Attach the referenced media or remove the invalid label.")
        if declared_labels - used:
            add("REFERENCE_LABEL_UNUSED", "review", "/attachments",
                "Verify whether the runtime uses each unlabeled or implicitly bound attachment.")
    elif attachments:
        add("REFERENCE_BINDING_OPAQUE", "review", "/binding/scheme",
            "Verify label-to-file bindings in the actual model adapter.")

    payload_hash = None
    if all(item["sha256"] is not None for item in payload_attachments):
        payload = {"model": data["model"], "parameters": data["parameters"],
                   "prompt": data["prompt"], "binding_scheme": binding["scheme"],
                   "attachments": payload_attachments}
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
        payload_hash = hashlib.sha256(encoded).hexdigest()
    return {
        "schema": SCHEMA,
        "status": "BLOCK" if any(x["severity"] == "block" for x in findings) else "REVIEW_REQUIRED",
        "scope": "declared_payload_and_local_file_hashes",
        "semantic_review": "not_performed",
        "asset_review": "not_performed",
        "keyframe_visual_review": "not_performed",
        "actual_model_submission_checked": False,
        "source_prompt_sha256": sha256_text(compiler["source_prompt"]),
        "prompt_sha256": sha256_text(data["prompt"]),
        "declared_payload_sha256": payload_hash,
        "attachments": checked,
        "findings": findings,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        with args.input.open("rb") as handle:
            raw = handle.read(MAX_INPUT_BYTES + 1)
        require(len(raw) <= MAX_INPUT_BYTES, "input too large")
        data = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_json,
                          parse_constant=lambda _: (_ for _ in ()).throw(InputError("invalid number")))
        result = audit(data)
        result["input_sha256"] = hashlib.sha256(raw).hexdigest()
    except (OSError, ValueError, UnicodeError, InputError, OverflowError, RecursionError) as exc:
        result = {"schema": SCHEMA, "status": "INVALID_INPUT",
                  "error": str(exc) if isinstance(exc, InputError) else "cannot read valid JSON",
                  "semantic_review": "not_performed",
                  "actual_model_submission_checked": False}
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 1 if result["status"] in ("BLOCK", "INVALID_INPUT") else 2


if __name__ == "__main__":
    sys.exit(main())
