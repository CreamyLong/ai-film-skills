#!/usr/bin/env python3
"""Create review evidence for burned-in text/captions on a generated clip.

This tool does not pass the clip and does not use OCR. It samples six frames,
crops the lower 45% where H3 usually burns text, and writes a contact sheet plus
a JSON report whose default status is ``review_required``. A reviewer must
inspect the sheet, record their name and issues, and set the status to
``reviewed``. The report binds the review to the video and sheet hashes.
Three samples miss short captions that appear late in
a clip, so six is the default; raise it with ``--samples`` for long clips.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from media_qc import file_sha256

FFPROBE = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "csv=p=0"]


def probe_duration(path: Path) -> float:
    proc = subprocess.run(FFPROBE + [str(path)], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip()[:300] or "ffprobe failed")
    return float(proc.stdout.strip())


def extract(path: Path, timestamp: float, out: Path) -> None:
    proc = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", f"{timestamp:.3f}", "-i", str(path),
         "-frames:v", "1", str(out)], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip()[:300] or "frame extraction failed")


def build_sheet(frames: list[Path], out: Path) -> None:
    inputs = []
    for frame in frames:
        inputs += ["-i", str(frame)]
    # Stack full frames and outline the lower 45% in each.
    filters = []
    for index in range(len(frames)):
        filters.append(f"[{index}:v]scale=300:-1,drawbox=x=0:y=ih*0.55:w=iw:h=ih*0.45:color=red@0.35:t=2[v{index}]")
    filters.append("".join(f"[v{i}]" for i in range(len(frames))) + f"hstack=inputs={len(frames)}[out]")
    proc = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(filters),
         "-map", "[out]", "-frames:v", "1", str(out)], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip()[:300] or "contact sheet failed")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--contact-sheet", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--samples", type=int, default=6,
                        help="number of evenly spaced frames to sample (default 6)")
    args = parser.parse_args(argv)
    try:
        video = args.video.resolve()
        sheet = (args.contact_sheet or video.with_name(video.stem + "_caption_review.jpg")).resolve()
        report_path = (args.report or video.with_name(video.stem + "_caption_review.json")).resolve()
        if len({video, sheet, report_path}) != 3:
            raise ValueError("video, contact sheet and report must be different files")
        video_hash = file_sha256(video)
        duration = probe_duration(video)
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("video duration must be positive and finite")
        count = max(2, args.samples)
        tail = max(0, duration - 0.05)
        times = [min(tail, duration * (i + 0.5) / count) for i in range(count)]
        with tempfile.TemporaryDirectory(prefix="caption-qc-") as raw:
            tmp = Path(raw)
            frames = []
            for index, timestamp in enumerate(times):
                frame = tmp / f"frame_{index}.png"
                extract(video, timestamp, frame)
                frames.append(frame)
            generated_sheet = tmp / sheet.name
            build_sheet(frames, generated_sheet)
            if file_sha256(video) != video_hash:
                raise ValueError("video changed during frame extraction")
            if not generated_sheet.stat().st_size:
                raise ValueError("contact sheet is empty")
            sheet_hash = file_sha256(generated_sheet)
            shutil.copyfile(generated_sheet, sheet)
        report = {
            "status": "review_required",
            "video": str(video),
            "video_sha256": video_hash,
            "duration_seconds": round(duration, 3),
            "sample_times": [round(value, 3) for value in times],
            "contact_sheet": sheet.name if sheet.parent == report_path.parent else str(sheet),
            "contact_sheet_sha256": sheet_hash,
            "reviewer": None,
            "issues": [],
            "note": "Inspect the full frames and the red-marked lower band for burned-in text. "
                    "Change status to 'reviewed' only after inspection; record reviewer and issues.",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
