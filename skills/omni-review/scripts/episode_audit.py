#!/usr/bin/env python3
"""Build an episode review evidence pack and optionally run the reviewer.

Reads an editlist and prompt file, then writes to --out:

  grids/block_<i>.jpg     one 10-12 frame timestamped grid per scene block
  identity/<shot>.jpg     one frame per dialogue shot (for reference pairing)
  audio/cut_<time>.wav    4 s around each scene boundary (A/B cut review)
  manifest.json           every task with its inputs and question

With --run, sends tasks to the configured omni model (budget-limited) and writes
results.json. Without --run it only builds evidence; no network call, no cost.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from omni_review import (AUDIO_QUESTION, IDENTITY_QUESTION, SHEET_QUESTION,  # noqa: E402
                         ask, data_url)

GRID_QUESTION = ("这是同一场戏的连续抽帧（每帧带时间码）。检查墙面、门窗、座椅、人群、"
                 "光源、固定陈设是否属于同一个房间；逐帧指出跳变，并区分机位变化与空间不一致。")


def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-2000:])


def duration(path: Path) -> float:
    proc = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                           "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return float(proc.stdout.strip())


def make_grid(video: Path, start: float, end: float, out: Path, count: int = 12) -> None:
    span = max(0.5, end - start)
    limit = max(0.0, duration(video) - 0.08)
    times = [min(limit, start + span * (i + 0.5) / count) for i in range(count)]
    frames = []
    last = None
    for index, moment in enumerate(times):
        frame = out.parent / f"_f{index}.jpg"
        frame.unlink(missing_ok=True)
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{moment:.3f}", "-i", str(video),
             "-frames:v", "1", "-vf", "scale=300:-2", str(frame)])
        if not frame.exists():
            if last is not None:
                frames.append(last.copy())
            continue
        image = Image.open(frame).convert("RGB")
        draw = ImageDraw.Draw(image)
        draw.rectangle([0, 0, 86, 18], fill=(0, 0, 0))
        draw.text((4, 4), f"{int(moment // 60):02d}:{moment % 60:05.2f}", fill=(255, 255, 0))
        frames.append(image)
        last = image
        frame.unlink(missing_ok=True)
    if not frames:
        raise RuntimeError(f"no frames extracted for {video}")
    columns = 4
    rows = (len(frames) + columns - 1) // columns
    cell_w = max(f.width for f in frames)
    cell_h = max(f.height for f in frames)
    sheet = Image.new("RGB", (cell_w * columns, cell_h * rows), (16, 16, 16))
    for index, image in enumerate(frames):
        sheet.paste(image, ((index % columns) * cell_w, (index // columns) * cell_h))
    sheet.save(out, quality=92)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--editlist", required=True, type=Path)
    parser.add_argument("--prompts", required=True, type=Path)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--characters", type=Path, default=None,
                        help='JSON map {"han": "path/to/face.png", ...}')
    parser.add_argument("--max-identity", type=int, default=4)
    parser.add_argument("--grids", type=int, default=3,
                        help="scene grids to build; chosen evenly across blocks")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--budget", type=int, default=8)
    args = parser.parse_args()

    root = args.editlist.resolve().parent.parent
    edit = json.loads(args.editlist.read_text(encoding="utf-8"))
    prompts = json.loads(args.prompts.read_text(encoding="utf-8"))
    shots = {shot["shot"]: shot for shot in prompts["shots"]}
    out = args.out
    for sub in ("grids", "identity", "audio"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    durations = {}
    for seg in edit["segments"]:
        if seg.get("still"):
            durations[seg["name"]] = float(seg["duration"])
        else:
            durations[seg["name"]] = duration(root / seg["src"])

    starts, cursor = {}, 0.0
    for seg in edit["segments"]:
        starts[seg["name"]] = cursor
        cursor += durations[seg["name"]]

    tasks = []
    blocks = edit["blocks"]
    if len(blocks) <= args.grids:
        chosen = list(range(len(blocks)))
    else:
        step = (len(blocks) - 1) / max(1, args.grids - 1)
        chosen = sorted({round(i * step) for i in range(args.grids)})
    for index in chosen:
        names = blocks[index]
        begin = starts[names[0]]
        end = starts[names[-1]] + durations[names[-1]]
        sheet = out / "grids" / f"block_{index}.jpg"
        make_grid(args.video, begin, end, sheet, count=12 if end - begin > 6 else 6)
        tasks.append({"id": f"T3-block{index}", "tier": "T3", "type": "sheet",
                      "inputs": [str(sheet)], "question": GRID_QUESTION,
                      "time_range": [round(begin, 2), round(end, 2)]})

    if args.characters and args.characters.exists():
        charmap = json.loads(args.characters.read_text(encoding="utf-8"))
    else:
        charmap = {}
    identity_done = 0
    for sid, shot in shots.items():
        if not shot.get("audio_refs") or identity_done >= args.max_identity:
            continue
        stem = Path(shot["audio_refs"][0]["file"]).stem
        speaker = stem.split("_")[0]
        faces = [r["file"] for r in shot.get("refs", [])
                 if "face" in Path(r["file"]).stem.lower()]
        matched = [f for f in faces if speaker in Path(f).stem.lower()]
        if matched:
            ref = str((root / matched[0]).resolve())
        elif len(faces) == 1:
            # speaker is off screen; still verify the on-screen listener's identity
            ref = str((root / faces[0]).resolve())
        else:
            ref = charmap.get(speaker)
        if not ref or not Path(ref).exists():
            continue
        src = root / "video" / "v1" / f"shot{sid}.mp4"
        if not src.exists():
            continue
        moment = max(0.5, durations[sid] * 0.4)
        frame = out / "identity" / f"shot{sid}.jpg"
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{moment:.3f}", "-i", str(src),
             "-frames:v", "1", str(frame)])
        tasks.append({"id": f"T1-shot{sid}", "tier": "T1", "type": "identity",
                      "inputs": [ref, str(frame)], "question": IDENTITY_QUESTION})
        identity_done += 1

    for index, names in enumerate(edit["blocks"][1:], start=1):
        boundary = starts[names[0]]
        begin = max(0.0, boundary - 2.0)
        clip = out / "audio" / f"cut_{boundary:07.2f}.wav"
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{begin:.3f}", "-t", "4.0",
             "-i", str(args.video), "-vn", "-ac", "1", "-ar", "16000", str(clip)])
        tasks.append({"id": f"T4-cut{boundary:.2f}", "tier": "T4", "type": "audio",
                      "inputs": [str(clip)], "question": AUDIO_QUESTION})
        if len([t for t in tasks if t["tier"] == "T4"]) >= 3:
            break

    manifest = {"episode": edit.get("episode", args.prompts.stem), "video": str(args.video),
                "duration": round(probe_duration(args.video), 3), "tasks": tasks}
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    print(f"built {len(tasks)} tasks -> {out/'manifest.json'}")

    if not args.run:
        return
    order = {"T1": 0, "T4": 1, "T2": 2, "T3": 3}
    ranked = sorted(tasks, key=lambda item: order.get(item["tier"], 9))
    results = []
    for task in ranked[:args.budget]:
        content = [{"type": "text", "text": task["question"]}]
        if task["type"] == "identity":
            content += [{"type": "image_url", "image_url": {"url": data_url(Path(task["inputs"][0]), "image/png")}},
                        {"type": "image_url", "image_url": {"url": data_url(Path(task["inputs"][1]), "image/jpeg")}}]
        elif task["type"] == "sheet":
            content.append({"type": "image_url", "image_url": {"url": data_url(Path(task["inputs"][0]), "image/jpeg")}})
        elif task["type"] == "audio":
            content.append({"type": "input_audio", "input_audio": {
                "data": data_url(Path(task["inputs"][0]), "audio/wav"), "format": "wav"}})
        try:
            result = ask(content, timeout=600)
            results.append({**task, "result": result})
            print(f"done {task['id']} ({result['latency_seconds']}s)")
        except Exception as exc:
            results.append({**task, "error": f"{type(exc).__name__}: {exc}"[:400]})
            print(f"fail {task['id']}: {exc}")
    (out / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2),
                                      encoding="utf-8")


def probe_duration(path: Path) -> float:
    return duration(path)


if __name__ == "__main__":
    main()
