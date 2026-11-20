#!/usr/bin/env python3
"""Check loudness continuity across independently generated shots.

Reads an episode editlist and prompt file, measures each source with
``volumedetect``, and reports:

* stills whose ``tone_from`` points at a shot that contains dialogue
  (the card then replays a line at low volume: "ghost speech");
* dialogue-shot level spread (a proxy for "every shot is its own room");
* optionally, cut-point RMS jumps in an assembled video.

Exit status is 0 when no blocker is found, 1 on blocker, 2 on input error.
This tool does not listen and does not prove artistic quality.
"""
from __future__ import annotations

import argparse
import array
import json
import math
from pathlib import Path
import subprocess
import sys

SPREAD_BLOCK_DB = 6.0
CUT_BLOCK_DB = 6.0
STILL_TONE_VOLUME = 0.9


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def mean_volume(path: Path) -> float:
    proc = run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect",
                "-f", "null", "-"])
    for line in proc.stderr.splitlines():
        if "mean_volume:" in line:
            return float(line.split("mean_volume:")[1].split("dB")[0])
    raise RuntimeError(f"no mean_volume for {path}")


def probe_duration(path: Path) -> float:
    proc = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "csv=p=0", str(path)])
    return float(proc.stdout.strip())


def pcm_mono(path: Path) -> array.array:
    proc = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1",
                           "-ar", "48000", "-f", "s16le", "-"], capture_output=True)
    samples = array.array("h")
    samples.frombytes(proc.stdout)
    return samples


def rms(samples: array.array, start: float, end: float, rate: int = 48000) -> float:
    first, last = int(start * rate), min(int(end * rate), len(samples))
    if last <= first:
        return 0.0
    total = sum(value * value for value in samples[first:last])
    return math.sqrt(total / (last - first)) / 32768


def db(value: float) -> float:
    return 20 * math.log10(max(value, 1e-9))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--editlist", required=True, type=Path)
    parser.add_argument("--prompts", required=True, type=Path)
    parser.add_argument("--video", type=Path, default=None,
                        help="assembled cut; enables cut-point RMS jumps")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    blockers: list[str] = []
    warnings: list[str] = []
    try:
        edit = json.loads(args.editlist.read_text(encoding="utf-8"))
        prompts = json.loads(args.prompts.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2

    root = args.editlist.parent.parent
    shots = {shot["shot"]: shot for shot in prompts["shots"]}
    speech = {sid for sid, shot in shots.items() if shot.get("audio_refs")}

    levels: dict[str, float] = {}
    for seg in edit["segments"]:
        name = seg["name"]
        if seg.get("still"):
            source = seg.get("tone_from")
            if not source:
                warnings.append(f"still {name}: no tone_from; only the episode bed covers it")
                continue
            tone_id = Path(source).stem.replace("shot", "")
            if tone_id in speech:
                blockers.append(
                    f"still {name}: tone_from shot{tone_id} contains dialogue; "
                    "the card replays a line (ghost speech)")
            path = root / source
        else:
            path = root / seg["src"]
        if path.exists():
            # gain_db is applied by the assembler; measure the level the
            # audience will actually hear, not the raw source.
            levels[name] = mean_volume(path) + float(seg.get("gain_db", 0.0))
        else:
            blockers.append(f"segment {name}: missing source {path}")

    dialogue_levels = [value for name, value in levels.items() if name in speech]
    if dialogue_levels:
        spread = max(dialogue_levels) - min(dialogue_levels)
        if spread > SPREAD_BLOCK_DB:
            blockers.append(
                f"dialogue level spread {spread:.1f} dB "
                f"(min {min(dialogue_levels):.1f}, max {max(dialogue_levels):.1f}); "
                "align shot gains before assembly")
        elif spread > 4.0:
            warnings.append(f"dialogue level spread {spread:.1f} dB; align to within 4 dB")

    cuts: list[dict] = []
    if args.video and args.video.exists():
        samples = pcm_mono(args.video)
        blocks = edit.get("blocks") or []
        block_of = {}
        for index, names in enumerate(blocks):
            for name in names:
                block_of[name] = index
        cursor = 0.0
        previous_block = None
        durations = []
        for seg in edit["segments"]:
            if seg.get("still"):
                durations.append((seg["name"], float(seg["duration"])))
            else:
                durations.append((seg["name"], probe_duration(root / seg["src"])))
        for index, (name, duration) in enumerate(durations[:-1]):
            cursor += duration
            block = block_of.get(name)
            next_name = durations[index + 1][0]
            next_block = block_of.get(next_name)
            if block is not None and next_block is not None and block != next_block:
                cursor -= 0.30  # scene fade shortens the timeline
                previous_block = next_block
                continue
            before = rms(samples, max(0.0, cursor - 0.35), max(0.0, cursor - 0.05))
            after = rms(samples, cursor + 0.05, cursor + 0.35)
            delta = db(after) - db(before)
            entry = {"cut": round(cursor, 3), "from": name, "to": next_name,
                     "delta_db": round(delta, 1)}
            cuts.append(entry)
            if abs(delta) > CUT_BLOCK_DB and (name in speech and next_name in speech):
                blockers.append(
                    f"cut {cursor:.2f}s {name}->{next_name}: {delta:+.1f} dB between "
                    "two dialogue shots")
            elif abs(delta) > 10.0:
                warnings.append(
                    f"cut {cursor:.2f}s {name}->{next_name}: {delta:+.1f} dB "
                    "(dialogue/ambience transition; check by ear)")

    report = {
        "status": "BLOCKED" if blockers else ("REVIEW" if warnings else "PASS"),
        "blockers": blockers,
        "warnings": warnings,
        "levels_db": {name: round(value, 1) for name, value in levels.items()},
        "cuts": cuts,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not args.json:
        for item in blockers:
            print(f"BLOCK {item}", file=sys.stderr)
        for item in warnings:
            print(f"WARN  {item}", file=sys.stderr)
    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
