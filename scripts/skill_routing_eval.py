#!/usr/bin/env python3
"""Measure Skill routing: does a request land on the intended module?

Two modes:

  --offline   lexical overlap between the request and each Skill's
              name/description. Cheap regression baseline, no API.
  --model     send the catalog (name + description) and the request to an
              OpenAI-compatible text model, ask for one Skill name; records
              top-1 accuracy and a confusion matrix.

Cases are authored fixtures: ``{"query": "...", "expect": "skill-name"}``.
This measures description discriminability, not a specific host's hidden
selector; use it to find collisions and missing trigger vocabulary.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]


def frontmatter(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^---\n(.*?)\n---", text, re.S)
    if not match:
        raise ValueError(f"{path}: no frontmatter")
    block = match.group(1)
    name = re.search(r"^name:\s*(.+)$", block, re.M).group(1).strip()
    desc = re.search(r"^description:\s*(.*)$", block, re.M).group(1).strip()
    if desc in {">", "|"}:
        start = block.index(desc) + len(desc)
        folded = []
        for line in block[start:].splitlines():
            if line.startswith(("metadata:", "version:", "status:")) and not line.startswith(" "):
                break
            folded.append(line.strip())
        desc = " ".join(part for part in folded if part)
    return name, desc


def load_skills() -> dict[str, str]:
    skills = {}
    for base in (ROOT / "skills", ROOT / "experimental"):
        for path in sorted(base.glob("*/SKILL.md")):
            name, desc = frontmatter(path)
            skills[name] = desc
    return skills


def tokens(text: str) -> set[str]:
    text = text.lower()
    words = set(re.findall(r"[a-z0-9][a-z0-9_-]+", text))
    han = re.findall(r"[\u4e00-\u9fff]", text)
    bigrams = {"".join(han[i:i + 2]) for i in range(len(han) - 1)}
    return words | bigrams


def lexical_rank(query: str, skills: dict[str, str]) -> list[tuple[str, float]]:
    q = tokens(query)
    q.discard("")
    scored = []
    for name, desc in skills.items():
        target = tokens(name.replace("-", " ") + " " + desc)
        overlap = q & target
        score = len(overlap) / math.sqrt(max(1, len(q)) * max(1, len(target)))
        if name in query.lower():
            score += 1.0
        scored.append((name, score))
    return sorted(scored, key=lambda item: item[1], reverse=True)


def model_rank(query: str, skills: dict[str, str], timeout: int) -> str:
    from openai import OpenAI
    import os
    key = os.environ.get("OMNI_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
    if not key:
        raise RuntimeError("set OMNI_API_KEY or DASHSCOPE_API_KEY for --model")
    client = OpenAI(api_key=key,
                    base_url=os.environ.get("OMNI_BASE_URL",
                                            "https://cn-beijing.maas.qianwenaiapi.com/compatible-mode/v1"),
                    timeout=timeout)
    catalog = "\n".join(f"- {name}: {desc}" for name, desc in skills.items())
    prompt = (
        "You are a Skill router. Choose exactly one Skill name from the catalog "
        "for the user request. Answer with JSON only: {\"skill\": \"name\"}.\n\n"
        f"Catalog:\n{catalog}\n\nRequest: {query}")
    response = client.chat.completions.create(
        model=os.environ.get("OMNI_MODEL", "qwen3.8-omni-flash"),
        messages=[{"role": "user", "content": prompt}],
        modalities=["text"])
    text = response.choices[0].message.content
    found = re.search(r"\{.*?\}", text, re.S)
    if not found:
        return ""
    try:
        return json.loads(found.group(0)).get("skill", "")
    except ValueError:
        return ""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--model", action="store_true")
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args(argv)
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    skills = load_skills()
    if not skills:
        print("no skills found", file=sys.stderr)
        return 2

    results = []
    for case in cases:
        query, expect = case["query"], case["expect"]
        if args.offline:
            ranked = lexical_rank(query, skills)
            results.append({"query": query, "expect": expect, "mode": "offline",
                            "predicted": ranked[0][0], "top3": [n for n, _ in ranked[:3]]})
        if args.model:
            predicted = model_rank(query, skills, args.timeout)
            results.append({"query": query, "expect": expect, "mode": "model",
                            "predicted": predicted, "top3": [predicted]})

    by_mode = defaultdict(list)
    for item in results:
        by_mode[item["mode"]].append(item)
    summary = {}
    for mode, items in by_mode.items():
        correct = sum(1 for item in items if item["predicted"] == item["expect"])
        recall = Counter(item["expect"] for item in items if item["predicted"] == item["expect"])
        totals = Counter(item["expect"] for item in items)
        confusion = Counter((item["expect"], item["predicted"]) for item in items
                            if item["predicted"] != item["expect"])
        summary[mode] = {
            "cases": len(items),
            "top1": round(correct / len(items), 3),
            "per_skill_recall": {name: f"{recall[name]}/{totals[name]}" for name in totals},
            "confusions": [{"expect": a, "predicted": b, "count": n}
                           for (a, b), n in confusion.most_common(15)],
        }
    report = {"summary": summary, "results": results}
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    if args.json_out:
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
