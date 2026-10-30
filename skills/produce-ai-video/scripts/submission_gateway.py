#!/usr/bin/env python3
"""Offline checks and immutable input snapshots for a controlled H3 submission."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import tempfile


def module(name):
    spec = importlib.util.spec_from_file_location(
        "film_" + name, Path(__file__).with_name(name + ".py"))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


ledger = module("production_state")
prompt_check = module("prompt_preflight")
shot_check = module("shot_preflight")
GateError = ledger.StateError
require = ledger.require


def label_mirror(timeline, generation_seconds):
    """Mirror the H3 manifest label order for the media this gateway can prove.

    Unsupported media is refused rather than truncated or guessed. The mirror is
    tied to the reviewed TimelineDirector file through the runtime dependency check.
    """
    images = [x for x in timeline.get("images", []) if isinstance(x, dict) and x.get("file")]
    require(len(images) <= 9, "image reference capacity exceeded; do not truncate")
    audios = [x for x in timeline.get("audios", []) if isinstance(x, dict) and x.get("file")]
    require(len(audios) == len([x for x in timeline.get("audios", []) if isinstance(x, dict)]),
            "audio entries without files are not allowed")
    require(all(str(x.get("audioMode") or "").lower() != "locked" for x in audios),
            "locked target soundtrack is not modelled by this gateway")
    require(len(audios) <= 3, "audio reference capacity exceeded; do not truncate")
    clips = [x for x in timeline.get("videoClips", []) if isinstance(x, dict) and x.get("file")]
    require(len(clips) == len([x for x in timeline.get("videoClips", []) if isinstance(x, dict)]),
            "video clip entries without files are not allowed")
    require(all(str(x.get("referenceMode") or "guide") == "guide" for x in clips),
            "only guide-mode video clips are modelled")
    selection = timeline.get("selection") or {}
    start = max(0.0, float(selection.get("start") or 0.0))
    end = start + max(0.0, float(selection.get("duration") or 5.0))
    require(end > 0 and (generation_seconds is None or float(generation_seconds) > 0),
            "generation timing is required")
    audio_enabled = timeline.get("videoAudioEnabled", True) is not False
    videos = []
    for clip in sorted(clips, key=lambda x: float(x.get("start") or 0.0)):
        clip_start = float(clip.get("start") or 0.0)
        clip_end = clip_start + float(clip.get("duration") or 0.0)
        overlap = min(end, clip_end) - max(start, clip_start)
        require(overlap > 0, "a clip outside the generated range must be removed from the timeline")
        require(overlap <= 15.0, "video reference longer than 15 seconds is not modelled")
        videos.append((clip, audio_enabled and clip.get("hasAudio", True) is not False))
    require(len(videos) <= 3, "video reference capacity exceeded; do not truncate")
    labelled = []
    for index, item in enumerate(images, 1):
        labelled.append(("image", f"<Picture {index}>", item["file"], False))
    for index, (clip, _) in enumerate(videos, 1):
        labelled.append(("video", f"<Video {index}>", clip["file"], False))
    for index, item in enumerate(audios, 1):
        labelled.append(("audio", f"<Audio {index}>", item["file"], False))
    number = len(audios)
    for clip, has_audio in videos:
        if has_audio:
            number += 1
            labelled.append(("audio", f"<Audio {number}>", clip["file"], True))
    return labelled, images + [clip for clip, _ in videos] + audios


def describe(graph, input_root):
    """No writes or model calls. The returned graph uses content-addressed inputs."""
    graph = copy.deepcopy(graph)
    root = Path(input_root).resolve()
    allowed_nodes = {
        "UNETLoader", "LoraLoaderModelOnly", "CLIPLoader", "VAELoader",
        "MiniMaxH3TimelineDirector", "KSamplerSelect", "BasicScheduler",
        "RandomNoise", "BasicGuider", "SamplerCustomAdvanced",
        "VAEDecode", "VAEDecodeAudio", "CreateVideo", "SaveVideo",
    }
    require(all(node.get("class_type") in allowed_nodes for node in graph.values()),
            "unsupported graph nodes; verify a new adapter rather than bypassing the gate")
    directors = [node["inputs"] for node in graph.values()
                 if node.get("class_type") == "MiniMaxH3TimelineDirector"]
    require(len(directors) == 1, "only one H3 TimelineDirector is supported")
    director = directors[0]
    timeline = json.loads(director["timeline_data"])
    labelled, items = label_mirror(timeline, director.get("generation_seconds"))
    cache = {}
    files = []
    for kind, label, name, derived in labelled:
        path = (root / name).resolve()
        require(path.is_relative_to(root), "input escapes configured input directory")
        if str(path) not in cache:
            sha = ledger.file_hash(path)
            suffix = path.suffix.lower()
            require(bool(re.fullmatch(r"\.[a-z0-9]{1,8}", suffix)), "unsupported input extension")
            snapshot = root / ".film-gate" / (sha + suffix)
            cache[str(path)] = (sha, snapshot)
        sha, snapshot = cache[str(path)]
        files.append({"kind": kind, "label": label, "path": str(path), "sha256": sha,
                      "snapshot": str(snapshot), "derived": derived})
    for item in items:
        path = (root / item["file"]).resolve()
        item["file"] = cache[str(path)][1].relative_to(root).as_posix()
    director["timeline_data"] = json.dumps(timeline, ensure_ascii=False, sort_keys=True)
    unets = [node["inputs"]["unet_name"] for node in graph.values()
             if node.get("class_type") == "UNETLoader"]
    require(len(unets) == 1, "one declared video model required")
    return {"graph": graph, "request_sha256": ledger.digest(graph),
            "generation_seconds": director.get("generation_seconds"),
            "model": unets[0], "prompt": director["prompt"], "files": files}


def checked(state_path, record_path, graph, input_root, prefix, runtime_files=()):
    require(bool(re.fullmatch(r"aifilm/[A-Za-z0-9_-]+", prefix)), "invalid generation prefix")
    aid = "submission:" + prefix.split("/")[-1]
    state = ledger.read_state(state_path)
    item = state["artifacts"].get(aid)
    require(item is not None and item["path"] == str(Path(record_path).resolve()),
            "register the exact local submission record before generation")
    require(not ledger.problems(state, aid), "submission or dependencies need current reviews")
    record = ledger.load_json(record_path)
    require(record.get("schema") == "film-skills.runtime-submission/v1", "invalid runtime record")
    require(record.get("scope") in ("shot", "film"), "explicit production scope required")
    actual = describe(graph, input_root)
    outputs = [node for node in actual["graph"].values() if node["class_type"] == "SaveVideo"]
    require(len(outputs) == 1 and outputs[0]["inputs"].get("filename_prefix") == prefix,
            "one matching output slot required")
    require(item["data"].get("request_sha256") == actual["request_sha256"],
            "actual graph changed; register and review a new submission")
    ids = ledger.closure(state, aid)
    dependencies = {key: state["artifacts"][key] for key in ids if key != aid}
    for runtime_file in runtime_files:
        require(any(value["kind"] == "asset" and value["data"].get("kind") == "runtime"
                    and value["path"] == str(Path(runtime_file).resolve())
                    for value in dependencies.values()),
                "current adapter/runtime code must be a reviewed dependency")
    kinds = {value["kind"] for value in dependencies.values()}
    required = {"director", "asset", "keyframe"}
    if record["scope"] == "film":
        required |= {"screenplay", "animatic"}
        if record.get("adaptation", True):
            required.add("source")
    require(required <= kinds, "missing reviewed upstream production stages")
    declaration = record["prompt_preflight"]
    for asset in declaration["asset_inventory"]["assets"]:
        current = dependencies.get(asset["id"])
        require(current and current["kind"] == "asset"
                and asset["version"] == current["fingerprint"],
                "asset inventory does not match the pinned production dependencies")
    require(declaration["model"] == actual["model"]
            and declaration["parameters"] == {"graph_sha256": actual["request_sha256"]}
            and declaration["prompt"] == actual["prompt"], "preflight is not the actual request")
    expected = [(x["kind"], x["label"], x["path"], x["sha256"]) for x in actual["files"]]
    declared = [(x["kind"], x["label"], x["path"], x["sha256"])
                for x in declaration["attachments"]]
    require(expected == declared, "actual attachment order, roles or files changed")
    approved = [value for value in dependencies.values()
                if value["path"] and value["kind"] in ("asset", "keyframe", "video")]
    approved_paths = {}
    for attachment in actual["files"]:
        matches = [value for value in approved if value["sha256"] == attachment["sha256"]]
        require(matches,
                "actual attachment is not a reviewed dependency")
        approved_paths[attachment["path"]] = matches
    images = [x for x in actual["files"] if x["kind"] == "image"]
    require(images and any(value["kind"] == "keyframe"
                           for value in approved_paths[images[0]["path"]]),
            "first composition reference must be a reviewed keyframe")
    require(declaration["attachments"][0]["role"] == "composition_reference",
            "Ref2VA references are not hard first-frame locks")
    prompt_report = prompt_check.audit(declaration)
    shot_report = shot_check.audit(record["shot_preflight"])
    reviewable = {"REFERENCE_BINDING_OPAQUE", "REFERENCE_LABEL_UNUSED",
                  "CROSS_SHOT_TIMING_UNVERIFIED", "STATE_HANDOFF_REQUIRES_REVIEW",
                  "CONTINUOUS_START_FRAME_REUSED"}
    resolutions = record.get("resolved_findings", [])
    used_resolutions = set()
    for checker, report in (("prompt", prompt_report), ("shot", shot_report)):
        for finding in report["findings"]:
            require(finding["severity"] == "review" and finding["code"] in reviewable,
                    "blocking or unknown preflight requirement; repair before submission")
            matches = [index for index, resolution in enumerate(resolutions)
                       if resolution.get("checker") == checker
                       and resolution.get("finding_sha256") == ledger.digest(finding)
                       and resolution.get("evidence_id") in dependencies]
            require(len(matches) == 1, "review finding needs a versioned evidence dependency")
            used_resolutions.add(matches[0])
    require(len(used_resolutions) == len(resolutions), "stale or unused finding resolutions")
    require(all(x["prompt_sha256"] == prompt_report["prompt_sha256"]
                for x in shot_report["prompts"]), "shot and prompt checks cover different text")
    require(prefix.split("/")[-1] in {x["shot_id"] for x in shot_report["prompts"]},
            "shot preflight does not cover this submission")
    audio_hashes = {x["sha256"] for x in actual["files"] if x["kind"] == "audio" and not x["derived"]}
    voice_assets = record.get("voice_assets", {})
    for shot in record["shot_preflight"]["shots"]:
        if shot["audio_route"] == "native":
            for dialogue in shot["dialogue"]:
                voice = dependencies.get(voice_assets.get(dialogue["speaker"]))
                require(voice and voice["kind"] == "asset"
                        and voice["data"].get("kind") == "voice"
                        and voice["sha256"] in audio_hashes,
                        "native speaker has no reviewed, actually attached voice reference")
    return state, aid, actual


def snapshots(files):
    for item in files:
        target = Path(item["snapshot"])
        target.parent.mkdir(exist_ok=True)
        if target.exists():
            require(ledger.file_hash(target) == item["sha256"], "immutable snapshot was changed")
            continue
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as handle:
                temporary = Path(handle.name)
                descriptor = os.open(item["path"], os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
                with os.fdopen(descriptor, "rb") as source:
                    require(stat.S_ISREG(os.fstat(source.fileno()).st_mode),
                            "snapshot source is not a regular file")
                    total = 0
                    while chunk := source.read(1024 * 1024):
                        total += len(chunk)
                        require(total <= ledger.MAX_FILE_BYTES, "snapshot exceeds hashing limit")
                        handle.write(chunk)
            require(ledger.file_hash(temporary) == item["sha256"], "input changed during snapshot")
            try:
                os.link(temporary, target)
            except FileExistsError:
                require(ledger.file_hash(target) == item["sha256"], "snapshot collision")
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)


def prepare(state_path, record_path, graph, input_root, prefix, runtime_files=()):
    _, aid, actual = checked(state_path, record_path, graph, input_root, prefix, runtime_files)
    snapshots(actual["files"])
    result = ledger.apply(state_path, {
        "action": "reserve", "id": aid, "request_sha256": actual["request_sha256"],
    })
    return {**actual, **result, "state_path": str(state_path), "submission": aid}


def receipt(ticket, status, payload, provider_job_id=None):
    parent = Path(ticket["state_path"]).parent / "production-receipts"
    parent.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=parent,
                                     suffix=".json", delete=False) as handle:
        path = Path(handle.name)
        json.dump({"request_sha256": ticket["request_sha256"], "payload": payload},
                  handle, ensure_ascii=False, allow_nan=False)
    return ledger.apply(ticket["state_path"], {
        "action": "receipt", "attempt": ticket["attempt"], "status": status,
        "provider_job_id": provider_job_id, "path": str(path),
    })


def bind(ticket, provider_job_id, output_id, path):
    return ledger.apply(ticket["state_path"], {
        "action": "bind", "attempt": ticket["attempt"], "provider_job_id": provider_job_id,
        "id": output_id, "path": str(Path(path).resolve()),
    })


def draft(graph, input_root, prefix):
    """Create only a blocked candidate; source facts and approvals are never inferred."""
    require(bool(re.fullmatch(r"aifilm/[A-Za-z0-9_-]+", prefix)), "invalid prefix")
    actual = describe(graph, input_root)
    prompt = actual["prompt"]
    require(isinstance(actual["generation_seconds"], (int, float))
            and actual["generation_seconds"] > 0, "candidate needs actual generation timing")
    return {
        "schema": "film-skills.runtime-submission/v1", "scope": "film", "adaptation": True,
        "request_sha256": actual["request_sha256"], "voice_assets": {},
        "prompt_preflight": {
            "schema": prompt_check.SCHEMA, "model": actual["model"],
            "parameters": {"graph_sha256": actual["request_sha256"]}, "prompt": prompt,
            "compiler": {"name": None, "version": None, "status": "unverified",
                         "scope": "unverified", "source_prompt": prompt,
                         "fallback_reason": None, "additions": []},
            "locks": {"required": [], "forbidden": []},
            "asset_inventory": {"coverage": "unverified", "assets": []},
            "binding": {"scheme": "h3_explicit",
                        "max_by_kind": {"image": None, "audio": None, "video": None},
                        "capacity_evidence": None},
            "attachments": [{
                "kind": item["kind"], "label": item["label"],
                "role": "composition_reference" if item["kind"] == "image" else
                        "paired_video_audio" if item["derived"] else
                        "voice_reference" if item["kind"] == "audio" else "continuation_guide",
                "path": item["path"], "sha256": item["sha256"],
                "review": {"status": "unverified", "sha256": None, "evidence": None},
            } for item in actual["files"]],
        },
        "shot_preflight": {
            "schema": shot_check.SCHEMA, "tracked_items": [], "shots": [{
                "id": prefix.split("/")[-1], "duration_seconds": actual["generation_seconds"],
                "prompt": prompt, "audio_route": "silent", "dialogue": [],
                "entry_state": {}, "exit_state": {},
            }],
        },
        "todo": ["Replace candidate timing, dialogue route, states and compiler source from facts.",
                 "Inventory all visible and anonymous subjects; bind reviewed dependencies.",
                 "Verify model capacity and actual sound/guide roles; review exact keyframes.",
                 "Register the completed record and obtain each scoped review; this draft is blocked."],
    }
