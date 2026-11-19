#!/usr/bin/env python3
"""Ask a multimodal reviewer about one artifact; print a JSON verdict.

Endpoint, model and key come from the environment:
  OMNI_BASE_URL  (default: DashScope compatible endpoint)
  OMNI_MODEL     (default: qwen3.8-omni-flash)
  OMNI_API_KEY   (falls back to DASHSCOPE_API_KEY)

The tool never accepts a key on the command line and does not write it to disk.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import time

DEFAULT_BASE = "https://cn-beijing.maas.qianwenaiapi.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3.8-omni-flash"


def data_url(path: Path, mime: str) -> str:
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def frame_at(video: Path, seconds: float) -> Path:
    out = Path("/tmp") / f"omni_frame_{video.stem}_{seconds:.2f}.jpg"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(seconds), "-i", str(video),
                    "-frames:v", "1", str(out)], check=True)
    return out


def ask(content: list[dict], timeout: int) -> dict:
    from openai import OpenAI
    key = os.environ.get("OMNI_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
    if not key:
        raise RuntimeError("set OMNI_API_KEY or DASHSCOPE_API_KEY")
    client = OpenAI(api_key=key,
                    base_url=os.environ.get("OMNI_BASE_URL", DEFAULT_BASE),
                    timeout=timeout)
    started = time.time()
    response = client.chat.completions.create(
        model=os.environ.get("OMNI_MODEL", DEFAULT_MODEL),
        messages=[{"role": "user", "content": content}],
        modalities=["text"])
    usage = response.usage
    return {
        "text": response.choices[0].message.content,
        "latency_seconds": round(time.time() - started, 1),
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
    }


IDENTITY_QUESTION = (
    "第一张是角色参考图，第二张是生成视频截图。判断是否同一人；若不是，"
    "列出至少三处面部或造型差异（眼镜、胡须、眉形、发际线、脸型、服装）。只回答判断与理由。")

SHEET_QUESTION = (
    "逐帧检查是否有烧录字幕、台词文字、伪 UI 或可读乱码；若有，指出第几帧、"
    "文字内容、画面位置。忽略抽检辅助线。")

VIDEO_QUESTION = (
    "检查这段视频：1) 有无多余手指、断肢、穿模、重复人物；2) 有无拖影、残影、"
    "半透明叠影；3) 有无无光源的漂浮粒子或贴图文字。指出秒数与位置，没有就说没有。")

AUDIO_QUESTION = (
    "两段音频各约4秒，中间都有一次镜头切换。判断哪一段在切点出现响度跳变、"
    "底噪变化、房间声断裂或爆音；指出秒数、类型、突兀程度1-5。")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="task", required=True)

    identity = sub.add_parser("identity")
    identity.add_argument("--ref", required=True, type=Path)
    identity.add_argument("--frame", required=True, type=Path)
    identity.add_argument("--at", type=float, default=1.0)
    identity.add_argument("--question", default=IDENTITY_QUESTION)

    sheet = sub.add_parser("sheet")
    sheet.add_argument("--image", required=True, type=Path)
    sheet.add_argument("--question", default=SHEET_QUESTION)

    video = sub.add_parser("video")
    video.add_argument("--file", required=True, type=Path)
    video.add_argument("--question", default=VIDEO_QUESTION)

    audio = sub.add_parser("audio")
    audio.add_argument("--file", required=True, type=Path, nargs="+")
    audio.add_argument("--question", default=AUDIO_QUESTION)

    for p in (identity, sheet, video, audio):
        p.add_argument("--timeout", type=int, default=600)

    args = parser.parse_args(argv)
    try:
        if args.task == "identity":
            frame = frame_at(args.frame, args.at) if args.frame.suffix.lower() == ".mp4" else args.frame
            content = [
                {"type": "text", "text": args.question},
                {"type": "image_url", "image_url": {"url": data_url(args.ref, "image/png")}},
                {"type": "image_url", "image_url": {"url": data_url(frame, "image/jpeg")}},
            ]
        elif args.task == "sheet":
            content = [{"type": "text", "text": args.question},
                       {"type": "image_url", "image_url": {"url": data_url(args.image, "image/jpeg")}}]
        elif args.task == "video":
            content = [{"type": "text", "text": args.question},
                       {"type": "video_url", "video_url": {"url": data_url(args.file, "video/mp4")}}]
        else:
            content = [{"type": "text", "text": args.question}]
            for path in args.file:
                content.append({"type": "input_audio", "input_audio": {
                    "data": data_url(path, "audio/wav"), "format": "wav"}})
        print(json.dumps({"status": "OK", "task": args.task, **ask(content, args.timeout)},
                         ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"[:600]},
                         ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
