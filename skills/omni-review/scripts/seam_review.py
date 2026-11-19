#!/usr/bin/env python3
"""Review the join between two clips: last frame of A, first frame of B.

Builds a labelled two-panel sheet plus a pair of 1 s audio clips, checks that
container-level specs match, and optionally asks the configured omni model
whether identity, space, axis, action and room tone carry across the cut.

Exit status is 0 unless an input error occurs. Findings are evidence for a human;
the tool never declares a cut passed.
"""
from __future__ import annotations

import argparse
import array
import json
import math
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from omni_review import ask, data_url  # noqa: E402

QUESTION = (
    "左图是 A 镜最后一帧，右图是 B 镜第一帧。先判断边界类型：同一动作续接、"
    "同场换视点、还是叙事跳跃。若允许主体变化，不要因为换了人就判错；只检查"
    "空间、光源、轴线、视线、动作方向是否合理。若是同镜续接，才要求同一角色、"
    "同一姿态、同一动作阶段。再指出有无重复帧、换脸或声场断裂。逐项给证据。")


def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-1500:] or f"failed: {cmd[0]}")


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout
    return float(out.strip())


def stream_info(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)],
                         capture_output=True, text=True).stdout
    data = json.loads(out)
    info = {}
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video" and "width" not in info:
            info.update(width=stream.get("width"), height=stream.get("height"),
                        fps=stream.get("r_frame_rate"), pix_fmt=stream.get("pix_fmt"))
        if stream.get("codec_type") == "audio" and "sample_rate" not in info:
            info.update(sample_rate=stream.get("sample_rate"), channels=stream.get("channels"))
    return info


def last_frame(clip: Path, out: Path) -> None:
    tail = max(0.0, duration(clip) - 0.12)
    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{tail:.3f}", "-i", str(clip),
         "-frames:v", "1", "-vf", "scale=420:-2", str(out)])


def first_frame(clip: Path, out: Path) -> None:
    run(["ffmpeg", "-y", "-v", "error", "-i", str(clip), "-frames:v", "1",
         "-vf", "scale=420:-2", str(out)])


def audio_pair(a: Path, b: Path, out_a: Path, out_b: Path) -> None:
    run(["ffmpeg", "-y", "-v", "error", "-sseof", "-1.0", "-i", str(a), "-vn",
         "-ac", "1", "-ar", "16000", str(out_a)])
    run(["ffmpeg", "-y", "-v", "error", "-t", "1.0", "-i", str(b), "-vn",
         "-ac", "1", "-ar", "16000", str(out_b)])


def rms(path: Path) -> float:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1",
                          "-ar", "16000", "-f", "s16le", "-"], capture_output=True).stdout
    samples = array.array("h")
    samples.frombytes(raw)
    if not samples:
        return 0.0
    return math.sqrt(sum(v * v for v in samples) / len(samples)) / 32768


def panel(left: Path, right: Path, out: Path) -> None:
    images = [Image.open(left).convert("RGB"), Image.open(right).convert("RGB")]
    width = sum(image.width for image in images)
    height = max(image.height for image in images)
    sheet = Image.new("RGB", (width, height), (12, 12, 12))
    x = 0
    for image, label in zip(images, ("A last", "B first")):
        sheet.paste(image, (x, 0))
        draw = ImageDraw.Draw(sheet)
        draw.rectangle([x, 0, x + 70, 18], fill=(0, 0, 0))
        draw.text((x + 4, 4), label, fill=(255, 255, 0))
        x += image.width
    sheet.save(out, quality=92)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a", required=True, type=Path, help="outgoing clip")
    parser.add_argument("--b", required=True, type=Path, help="incoming clip")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--type", choices=("auto", "same-take", "same-scene", "jump"),
                        default="auto", help="boundary type; auto lets the model classify")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    info_a, info_b = stream_info(args.a), stream_info(args.b)
    specs = {key: {"a": info_a.get(key), "b": info_b.get(key)}
             for key in ("width", "height", "fps", "pix_fmt", "sample_rate", "channels")}
    mismatches = [key for key, value in specs.items()
                  if value["a"] is not None and value["a"] != value["b"]]

    last = args.out / "a_last.jpg"
    first = args.out / "b_first.jpg"
    last_frame(args.a, last)
    first_frame(args.b, first)
    sheet = args.out / "seam.jpg"
    panel(last, first, sheet)

    tail_a = args.out / "a_tail.wav"
    head_b = args.out / "b_head.wav"
    audio_pair(args.a, args.b, tail_a, head_b)
    level_a, level_b = rms(tail_a), rms(head_b)
    db_a = 20 * math.log10(max(level_a, 1e-9))
    db_b = 20 * math.log10(max(level_b, 1e-9))
    jump = db_b - db_a

    report = {
        "a": str(args.a), "b": str(args.b),
        "spec_mismatches": mismatches,
        "audio_level_db": {"a_tail": round(db_a, 1), "b_head": round(db_b, 1),
                           "jump": round(jump, 1)},
        "sheet": str(sheet),
        "severity_hint": ("major" if mismatches or abs(jump) > 6 else "review"),
        "note": "Seam evidence only. A human confirms the cited frame and second.",
    }
    if args.run:
        hint = {"same-take": "边界类型：同一动作续接。",
                "same-scene": "边界类型：同场换视点，允许换主体。",
                "jump": "边界类型：叙事跳跃，允许时间/地点变化。"}.get(args.type, "")
        visual = ask([
            {"type": "text", "text": hint + QUESTION},
            {"type": "image_url", "image_url": {"url": data_url(sheet, "image/jpeg")}},
        ], timeout=600)
        sound = ask([
            {"type": "text", "text": "第一段是 A 镜最后 1 秒，第二段是 B 镜最前 1 秒。"
                                     "判断切点有无响度跳变、底噪变化、房间声断裂或爆音；"
                                     "指出类型与突兀程度 1-5。"},
            {"type": "input_audio", "input_audio": {
                "data": data_url(tail_a, "audio/wav"), "format": "wav"}},
            {"type": "input_audio", "input_audio": {
                "data": data_url(head_b, "audio/wav"), "format": "wav"}},
        ], timeout=600)
        report["model"] = {"visual": visual, "sound": sound}
    (args.out / "seam.json").write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                        encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
