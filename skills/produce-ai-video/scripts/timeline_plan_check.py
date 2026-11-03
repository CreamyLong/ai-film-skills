#!/usr/bin/env python3
"""Offline check of a MiniMax H3 TimelineDirector ``timeline_data`` plan.

Mirrors how ComfyUI-MiniMaxH3-TimelineDirector (behaviour verified against
plugin commit 050226d) turns a timeline into per-segment H3 inputs: segment
windows, <Picture N>/<Video N>/<Audio N> label order, fixed guides, and the
final soundtrack route. It reports every place where the plugin would silently
drop, renumber, lock or mute input. No media is decoded and no model is called;
structure passing never approves the generated result.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import sys

PLUGIN_REFERENCE = "050226d"
FPS = 24
MAX_IMAGES, MAX_VIDEOS, MAX_AUDIOS, MAX_TOTAL = 9, 3, 3, 12
MAX_VIDEO_SECONDS = 15.0
MIN_VIDEO_SECONDS = 5.0 / FPS
MAX_SEGMENT_FRAMES = 3592
MAX_SEGMENTS = 64
TRAINED_FRAMES = (124, 362)
REFERENCE_MODES = {"guide", "edit", "boundary"}
AUDIO_INTENTS = {"generate", "locked_audio", "video_original", "silent"}
RUNTIMES = {"finite_segment", "director"}
LABEL = re.compile(r"<(Picture|Video|Audio) ([1-9][0-9]*)>")


def _f(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def valid_overlap(frames):
    """Overlap values the planner accepts: 0, 1, or 5 + 17*n."""
    return frames == 0 or frames == 1 or (frames >= 5 and frames % 17 == 5)


def on_grid(frames):
    return frames >= 5 and (frames - 5) % 17 == 0


def aligned_length(seconds):
    requested = max(5.0 / FPS, float(seconds)) * FPS
    return int(5 + 17 * max(0, round((requested - 5.0) / 17.0)))


class Report:
    def __init__(self):
        self.findings = []

    def add(self, code, severity, location, advice):
        self.findings.append({"code": code, "severity": severity, "location": location,
                              "repair_direction": advice})


def _check_media_path(report, location, name):
    path = PurePosixPath(str(name).replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or re.match(r"^[A-Za-z]:", str(name)):
        report.add("MEDIA_PATH_OUTSIDE_INPUT", "block", location,
                   "Copy the file under the ComfyUI input directory and reference it by a relative path.")


def _video_pieces(clips, window_start, window_end, audio_enabled):
    """Prompt-addressable video references for one generation window (all modes)."""
    pieces, short = [], []
    for clip in sorted(clips, key=lambda c: _f(c.get("start"))):
        clip_start = _f(clip.get("start"))
        clip_end = clip_start + max(0.0, _f(clip.get("duration")))
        start, end = max(window_start, clip_start), min(window_end, clip_end)
        if end - start <= 0:
            continue
        remaining = end - start
        if remaining < MIN_VIDEO_SECONDS:
            short.append(clip)
        cursor = _f(clip.get("trimStart")) + start - clip_start
        while remaining >= MIN_VIDEO_SECONDS:
            piece = min(MAX_VIDEO_SECONDS, remaining)
            pieces.append({"clip": clip, "source_start": round(cursor, 6),
                           "duration": round(piece, 6), "timeline_start": round(start, 6),
                           "has_audio": audio_enabled and clip.get("hasAudio", True) is not False})
            cursor += piece
            start += piece
            remaining -= piece
    return pieces, short


def _guides(clips, window_start, window_end, length):
    guides = []
    for clip in sorted(clips, key=lambda c: _f(c.get("start"))):
        clip_start = _f(clip.get("start"))
        clip_end = clip_start + max(0.0, _f(clip.get("duration")))
        start, end = max(window_start, clip_start), min(window_end, clip_end)
        if end - start <= 0:
            continue
        mode = str(clip.get("referenceMode") or "guide")
        mode = mode if mode in REFERENCE_MODES else "guide"
        if mode == "edit":
            continue
        first = 0 if abs(start - window_start) <= 0.5 / FPS else max(0, round((start - window_start) * FPS))
        if mode == "boundary":
            guides.append({"clip_id": clip.get("id"), "kind": "boundary", "first_frame": first})
            continue
        frames = min(max(1, round((end - start) * FPS)), length)
        if first and abs(end - window_end) <= 0.5 / FPS:
            first = max(0, length - frames)
        guides.append({"clip_id": clip.get("id"), "kind": "fixed_guide",
                       "first_frame": min(first, max(0, length - frames)), "frames": frames})
    return guides


def _segments(timeline, report, generation_seconds):
    config = timeline.get("segmentConfig") if isinstance(timeline.get("segmentConfig"), dict) else {}
    count = int(_f(config.get("count"), 0))
    if count < 1:
        selection = timeline.get("selection") or {}
        seconds = generation_seconds if generation_seconds is not None else _f(selection.get("duration"), 5.0)
        length = aligned_length(seconds)
        if abs(float(seconds) * FPS - length) > 0.5:
            report.add("GENERATION_LENGTH_SNAPPED", "review", "/generation_seconds",
                       f"{seconds}s resolves to {length} frames ({length / FPS:.3f}s); declare the aligned duration.")
        start = max(0.0, _f(selection.get("start")))
        return [{"index": 1, "window_start": start, "length": length, "start_frame": 0,
                 "end_frame": length, "overlap": 0, "images": None, "audios": None,
                 "prompt": ""}], False
    segments = config.get("segments") if isinstance(config.get("segments"), list) else []
    if config.get("mode") != "timeline" or not 1 <= count <= MAX_SEGMENTS or len(segments) != count:
        report.add("SEGMENT_CONFIG_INVALID", "block", "/segmentConfig",
                   'Use mode "timeline", 1-64 segments, and exactly count segment entries.')
        return [], True
    result, previous_start, previous_end, previous_length = [], 0, 0, 0
    for index, segment in enumerate(segments, 1):
        loc = f"/segmentConfig/segments/{index}"
        start, end = segment.get("startFrame"), segment.get("endFrame")
        if type(start) is not int or type(end) is not int:
            report.add("SEGMENT_FRAMES_INVALID", "block", loc, "startFrame and endFrame must be integers.")
            continue
        length = end - start
        overlap = previous_end - start if index > 1 else 0
        if start < 0 or not on_grid(length) or length > MAX_SEGMENT_FRAMES:
            report.add("SEGMENT_LENGTH_OFF_GRID", "block", loc,
                       "Segment length must be 5 + 17*n frames and at most 3592.")
        elif not TRAINED_FRAMES[0] <= length <= TRAINED_FRAMES[1]:
            report.add("SEGMENT_OUTSIDE_TRAINED_RANGE", "review", loc,
                       "H3 is trained on about 124-362 frames (5-15 s); longer or shorter segments are "
                       "accepted by the plugin but quality is unverified.")
        if index == 1 and start != 0:
            report.add("SEGMENT_SEQUENCE_INVALID", "block", loc, "The first segment must start at frame 0.")
        if index > 1 and (start <= previous_start or end <= previous_end or overlap < 0
                          or overlap >= min(length, previous_length) or not valid_overlap(overlap)):
            report.add("SEGMENT_SEQUENCE_INVALID", "block", loc,
                       "Advance without gaps; overlap must be 0, 1 or 5 + 17*n frames and shorter than both segments.")
        result.append({"index": index, "window_start": start / FPS, "length": length,
                       "start_frame": start, "end_frame": end, "overlap": overlap,
                       "images": segment.get("images") if isinstance(segment.get("images"), list) else [],
                       "audios": segment.get("audios") if isinstance(segment.get("audios"), list) else [],
                       "prompt": str(segment.get("prompt") or "").strip()})
        previous_start, previous_end, previous_length = start, end, length
    return result, True


def _segment_assets(pool, ids, limit, report, location, kind):
    by_id = {str(a.get("id")): a for a in pool if isinstance(a, dict) and a.get("id") and a.get("file")}
    chosen, seen = [], set()
    for value in ids:
        key = str(value)
        if key not in by_id:
            report.add("SEGMENT_ASSET_UNKNOWN", "block", location,
                       f"{kind} id {key!r} is not in the global library; the plugin drops it silently.")
            continue
        if key not in seen:
            chosen.append(by_id[key])
            seen.add(key)
    if len(chosen) > limit:
        report.add("SEGMENT_CAPACITY_EXCEEDED", "block", location,
                   f"More than {limit} {kind} references; extra items are dropped silently. Remove them.")
    return chosen[:limit]


def _audio_mode(asset):
    return "locked" if str(asset.get("audioMode") or "").lower() == "locked" else "reference"


def audit(payload):
    report = Report()
    raw = payload.get("timeline_data")
    try:
        timeline = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError as exc:
        timeline = None
        report.add("TIMELINE_INVALID", "block", "/timeline_data", f"Invalid JSON: {exc}.")
    if not isinstance(timeline, dict):
        if not report.findings:
            report.add("TIMELINE_INVALID", "block", "/timeline_data", "timeline_data must be a JSON object.")
        return result(report, [], None, 0)

    width, height = payload.get("width"), payload.get("height")
    for name, value in (("width", width), ("height", height)):
        if value is not None and (not isinstance(value, int) or value % 32 or value < 32):
            report.add("CANVAS_OFF_GRID", "block", f"/{name}", "Canvas sides must be multiples of 32.")

    images = [a for a in timeline.get("images", []) if isinstance(a, dict)]
    audios = [a for a in timeline.get("audios", []) if isinstance(a, dict)]
    clips = [c for c in timeline.get("videoClips", []) if isinstance(c, dict)]
    for kind, items in (("image", images), ("audio", audios), ("video", clips)):
        for position, item in enumerate(items, 1):
            loc = f"/{kind}s/{position}"
            if not item.get("file"):
                report.add("MEDIA_FILE_MISSING", "block", loc, "Every entry needs a file; the plugin skips empty ones.")
            else:
                _check_media_path(report, loc, item["file"])
    clips = [c for c in clips if c.get("file")]
    for position, clip in enumerate(clips, 1):
        loc = f"/videoClips/{position}"
        mode = clip.get("referenceMode")
        if mode is None:
            report.add("REFERENCE_MODE_IMPLICIT", "block", loc,
                       'Set referenceMode explicitly. Omitted means "guide" (hard frame lock) in the API, '
                       'while the UI defaults new uploads to "edit".')
        elif mode not in REFERENCE_MODES:
            report.add("REFERENCE_MODE_INVALID", "block", loc,
                       f'Unknown referenceMode {mode!r} silently becomes "guide"; use guide, edit or boundary.')
        if "hasAudio" not in clip:
            report.add("CLIP_AUDIO_IMPLICIT", "block", loc,
                       "Declare hasAudio. An omitted value is treated as true and can lock the final soundtrack.")
    if clips and "videoAudioEnabled" not in timeline:
        report.add("VIDEO_AUDIO_IMPLICIT", "block", "/videoAudioEnabled",
                   "Declare videoAudioEnabled whenever video clips are present; it decides lock, mute or generate.")

    runtime = payload.get("runtime", "finite_segment")
    if runtime not in RUNTIMES:
        report.add("RUNTIME_INVALID", "block", "/runtime", "Use finite_segment or director.")
        return result(report, [], None, 0)
    generation_seconds = payload.get("generation_seconds")
    windows, segmented = _segments(timeline, report, generation_seconds)
    global_prompt = str(timeline.get("globalPrompt") or "").strip()
    single_prompt = str(payload.get("prompt") or "").strip()
    prompts_filled = [w["prompt"] for w in windows if w["prompt"]]
    if runtime == "director" and segmented:
        report.add("SEGMENTS_NEED_FINITE_SAMPLER", "block", "/segmentConfig",
                   "The compatibility director renders one window; feed segments through "
                   "Material Planner -> Finite Segment Sampling.")
    elif segmented and windows:
        if prompts_filled and len(prompts_filled) != len(windows):
            missing = [str(w["index"]) for w in windows if not w["prompt"]]
            report.add("SEGMENT_PROMPTS_INCOMPLETE", "block", "/segmentConfig/segments",
                       "Once any segment has its own prompt every segment needs one (missing: "
                       + ", ".join(missing) + ").")
        elif not prompts_filled and not global_prompt:
            report.add("PROMPT_MISSING", "block", "/globalPrompt",
                       "Provide a globalPrompt or a prompt for every segment.")
    elif windows and runtime == "director" and not single_prompt:
        report.add("PROMPT_MISSING", "block", "/prompt", "The compatibility director needs its node prompt.")
    elif windows and runtime == "finite_segment" and not global_prompt:
        report.add("PROMPT_MISSING", "block", "/globalPrompt",
                   "An unsegmented Material Planner plan uses globalPrompt; it is empty.")

    audio_enabled = timeline.get("videoAudioEnabled", True) is not False
    segments_out, locks = [], []
    for window in windows:
        loc = f"segment {window['index']}"
        if window["images"] is None:
            seg_images = [a for a in images if a.get("file")]
            seg_audios = [a for a in audios if a.get("file")]
            if len(seg_images) > MAX_IMAGES:
                report.add("SEGMENT_CAPACITY_EXCEEDED", "block", loc,
                           "More than 9 images; the 10th and later are dropped silently.")
            seg_images = seg_images[:MAX_IMAGES]
        else:
            seg_images = _segment_assets(images, window["images"], MAX_IMAGES, report, loc, "image")
            seg_audios = _segment_assets(audios, window["audios"], MAX_AUDIOS, report, loc, "audio")
        window_end = window["window_start"] + window["length"] / FPS
        pieces, short = _video_pieces(clips, window["window_start"], window_end, audio_enabled)
        for clip in short:
            report.add("VIDEO_INTERSECTION_TOO_SHORT", "block", f"{loc}/{clip.get('id')}",
                       "The clip covers under 5 frames of this window and is ignored as a reference; "
                       "extend the overlap or remove the clip.")
        if len(pieces) > MAX_VIDEOS:
            report.add("SEGMENT_CAPACITY_EXCEEDED", "block", loc,
                       "More than 3 video reference windows (clips over 15 s split into several); "
                       "later ones are dropped silently.")
        pieces = pieces[:MAX_VIDEOS]
        if sum(p["duration"] for p in pieces) > MAX_VIDEO_SECONDS + 1e-6:
            report.add("VIDEO_REFERENCE_TOO_LONG", "block", loc,
                       "Total video reference exceeds the official 15 s per generation.")
        reference_audios = [a for a in seg_audios if _audio_mode(a) != "locked"]
        locked = [a for a in seg_audios if _audio_mode(a) == "locked"]
        if len(locked) > 1:
            report.add("LOCKED_AUDIO_MULTIPLE", "block", loc, "At most one locked soundtrack per segment.")
        pictures = [{"label": f"<Picture {i}>", "file": a["file"], "id": a.get("id")}
                    for i, a in enumerate(seg_images, 1)]
        videos = [{"label": f"<Video {i}>", "file": p["clip"]["file"], "clip_id": p["clip"].get("id"),
                   "mode": str(p["clip"].get("referenceMode") or "guide"),
                   "source_start": p["source_start"], "duration": p["duration"]}
                  for i, p in enumerate(pieces, 1)]
        audio_labels = [{"label": f"<Audio {i}>", "source": "standalone", "file": a["file"], "id": a.get("id")}
                        for i, a in enumerate(reference_audios, 1)]
        for number, piece in enumerate(pieces, 1):
            if piece["has_audio"]:
                audio_labels.append({"label": f"<Audio {len(audio_labels) + 1}>",
                                     "source": f"paired with <Video {number}>", "file": piece["clip"]["file"]})
        total = len(pictures) + len(videos) + len(audio_labels)
        if total > MAX_TOTAL:
            report.add("TOTAL_REFERENCES_EXCEEDED", "block", loc,
                       f"{total} references exceed the official total of 12.")
        video_soundtrack = audio_enabled and any(c.get("hasAudio", True) is not False and _f(c.get("duration")) > 0
                                                 for c in clips)
        if locked:
            locks.append(("audio", locked[0]["file"], round(_f(locked[0].get("trimStart")), 6)))
        elif video_soundtrack:
            locks.append(("video", None, None))
        else:
            locks.append(None)

        prompt = window["prompt"] or (single_prompt if runtime == "director" else global_prompt)
        if prompt:
            limits = {"Picture": len(pictures), "Video": len(videos), "Audio": len(audio_labels)}
            for kind, number in {(m.group(1), int(m.group(2))) for m in LABEL.finditer(prompt)}:
                if number > limits[kind]:
                    report.add("PROMPT_LABEL_OUT_OF_RANGE", "block", f"{loc}/<{kind} {number}>",
                               f"This segment exposes only {limits[kind]} {kind} label(s); renumber per segment.")
            if window["overlap"] > 0 and "[Shot 1]" not in prompt:
                report.add("CONTINUATION_SHOT1_MISSING", "block", loc,
                           "A continued segment must open with [Shot 1] describing the carried overlap.")
            elif window["overlap"] > 0:
                report.add("CONTINUATION_SHOT1_REVIEW", "review", loc,
                           f"Confirm [Shot 1] first restates the carried {window['overlap']}-frame "
                           f"({window['overlap'] / FPS:.3f}s) overlap before new action; the main "
                           "Planner path does not inject this for you.")
        segments_out.append({
            "index": window["index"], "start_frame": window["start_frame"],
            "end_frame": window["end_frame"], "length": window["length"],
            "overlap_frames": window["overlap"],
            "kept_frames": window["length"] - window["overlap"],
            "labels": {"pictures": pictures, "videos": videos, "audios": audio_labels},
            "locked_audio": locked[0]["file"] if locked else None,
            "guides": _guides(clips, window["window_start"], window_end, window["length"]),
        })

    if runtime == "director":
        if any(lock and lock[0] == "audio" for lock in locks):
            report.add("LOCKED_AUDIO_NEEDS_FINITE_SAMPLER", "block", "/audios",
                       "Locked original audio is honoured only by Finite Segment Sampling.")
        route = "generate" if windows else None
    else:
        route = _audio_route(report, locks, clips, timeline)
    intent = payload.get("audio_intent")
    if intent is not None and intent not in AUDIO_INTENTS:
        report.add("AUDIO_INTENT_INVALID", "block", "/audio_intent",
                   "Use generate, locked_audio, video_original or silent.")
    elif intent is not None and route and intent != route:
        report.add("AUDIO_ROUTE_MISMATCH", "block", "/audio",
                   f"The plan produces {route!r} audio but {intent!r} was intended; see the audio routing rules.")
    elif intent is None and route in {"video_original", "silent", "locked_audio"}:
        report.add("AUDIO_ROUTE_FIXED", "review", "/audio",
                   f"Final soundtrack is {route!r}; H3 will not generate new sound. Declare audio_intent to confirm.")

    _check_second_pass(report, timeline, payload.get("sampler") or {})
    target = windows[-1]["end_frame"] if windows else 0
    return result(report, segments_out, route, target)


def _audio_route(report, locks, clips, timeline):
    if not locks:
        return None
    if any(locks) and not all(locks):
        report.add("LOCKED_AUDIO_PARTIAL", "block", "/audios",
                   "A locked soundtrack (or locked video audio) must cover every segment.")
        return None
    if all(locks):
        if len({lock for lock in locks}) != 1:
            report.add("LOCKED_AUDIO_INCONSISTENT", "block", "/audios",
                       "Every segment must lock the same audio file and source-in point.")
        return "locked_audio" if locks[0][0] == "audio" else "video_original"
    if clips and timeline.get("videoAudioEnabled", True) is False:
        return "silent"
    return "generate"


def _check_second_pass(report, timeline, sampler):
    if not timeline.get("secondPass"):
        return
    if not str(timeline.get("secondPassModel") or "").strip():
        report.add("SECOND_PASS_MODEL_MISSING", "block", "/secondPassModel",
                   "Name an H3 latent upscaler from models/latent_upscale_models.")
    high = timeline.get("secondPassHighSteps")
    steps = sampler.get("steps")
    if type(high) is not int or high < 1:
        report.add("SECOND_PASS_STEPS_INVALID", "block", "/secondPassHighSteps",
                   "High-resolution steps must be a positive integer.")
    elif isinstance(steps, int) and high >= steps:
        report.add("SECOND_PASS_STEPS_INVALID", "block", "/secondPassHighSteps",
                   "High-resolution steps must be fewer than the scheduler's total steps (about 25% recommended).")
    name = sampler.get("name")
    if name is not None and name != "euler":
        report.add("SECOND_PASS_SAMPLER", "block", "/sampler",
                   "Two-stage sampling requires the standard euler sampler (s_churn 0).")


def result(report, segments, route, target_frames):
    return {"status": "BLOCK" if any(f["severity"] == "block" for f in report.findings) else "REVIEW_REQUIRED",
            "plugin_reference": PLUGIN_REFERENCE, "segments": segments, "audio_route": route,
            "target_output_frames": target_frames, "media_review": "not_performed",
            "findings": report.findings}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("payload", help="JSON payload with timeline_data and optional width/height/"
                                        "generation_seconds/prompt/audio_intent/sampler")
    args = parser.parse_args(argv)
    try:
        report = audit(json.loads(Path(args.payload).read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, AttributeError, TypeError, ValueError) as exc:
        print(json.dumps({"status": "INVALID_INPUT", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "BLOCK" else 0


if __name__ == "__main__":
    sys.exit(main())
