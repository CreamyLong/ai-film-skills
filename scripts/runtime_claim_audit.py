#!/usr/bin/env python3
"""Inventory runtime claims that lack an evidence marker.

Advisory only: lists Skill documents that talk about model/plugin behaviour
("实测", "官方", "必须", "不能", "会") without an evidence header, a link to
docs/RUNTIME_CLAIMS.md, or an explicit unverified/ASSUMED marker.

It does not judge whether a claim is true; a human reviews each file.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
CLAIM = re.compile(r"实测|官方|必须|不能|会(?:把|被|在|自行|生成|说|出现)")
MODEL = re.compile(r"H3|ComfyUI|MiniMax|omni|Omni|TTS|Qwen|qwen|模型|插件")
MARKER = re.compile(r"证据状态|RUNTIME_CLAIMS|ASSUMED|unverified|未核实")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    rows = []
    for path in sorted(ROOT.glob("skills/**/*.md")):
        text = path.read_text(encoding="utf-8")
        if not (CLAIM.search(text) and MODEL.search(text)):
            continue
        if MARKER.search(text):
            continue
        lines = [line.strip() for line in text.splitlines()
                 if CLAIM.search(line) and MODEL.search(line)]
        rows.append({"file": str(path.relative_to(ROOT)), "examples": lines[:3]})
    print(f"{len(rows)} file(s) with runtime claims and no evidence marker")
    for row in rows:
        print(f"- {row['file']}")
        for example in row["examples"]:
            print(f"    {example[:120]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
