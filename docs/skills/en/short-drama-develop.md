# short-drama-develop — series development and episode map

| Status | Adapted from the MIT drama-skills suite; structural checks and self-tests only, no real-task or user-acceptance evidence yet. |
|---|---|
| Can deliver alone | Series-level development package producing the 项目开发/ contract set; pairs naturally with the episode-writing package but runs alone for planning-only requests. |
| Cannot claim alone | It does not write scene action or dialogue, split assets, write prompts, generate media, or issue final review verdicts. |

[Runtime `SKILL.md`](../../../skills/short-drama-develop/SKILL.md) · [Install current source](../../INSTALLATION.md) · [Install](../../INSTALLATION.md) · [Compatibility](../../COMPATIBILITY.md) · [Design system](../../SKILL_DESIGN_SYSTEM.md)

No release snapshot yet; install from the current source tree. MIT license retained in package LICENSE.

<!-- contract:purpose -->
## 1. Purpose

Develop a short-drama or comic-drama idea, novel, or notes into a traceable creative brief, story engine, optional director brief, adaptation map, and full episode map with per-episode entry/exit states.

<!-- contract:principles -->
## 2. Design principles

- Build series story from causality, character state, and precise handoff facts before any production contract; a premise, outline, or episode map is not a substitute for the requested full script.
- Separate creator-proposed values from creator-accepted facts; inferred settings are marked as inferred and confirmed before they harden into canon.
- Genre cards, hook patterns, and rhythm profiles are optional calibrated aids, never mandatory templates or quality proof.
- Genre cards calibrate internally only and never appear in deliverables; episode count and hook placement follow the creator's contract, not fixed formulas.
- Premise devices separate the creator-accepted contract from in-fiction disclosure; an ability without a contract clause is retroactive widening.

<!-- contract:standalone -->
## 3. Standalone scope

Use this module by itself when the requested result stays inside the following boundary:

Series-level development package producing the 项目开发/ contract set; pairs naturally with the episode-writing package but runs alone for planning-only requests.

**Cannot claim alone:** It does not write scene action or dialogue, split assets, write prompts, generate media, or issue final review verdicts.

<!-- contract:inputs -->
## 4. Inputs

- A premise, idea, genre, audience, world/era, core hook, visual form, episode count, language, or existing notes/novel/materials, plus the requested deliverable.
- Accepted creative decisions pass downstream unchanged; missing values stay pending, inferred values stay marked.
- Long multi-episode source material enters through the exact-byte intake index, never whole-file context dumps.

<!-- contract:workflow -->
## 5. Workflow

1. Lock the creator contract, explore mechanism-different directions when undecided, build the story engine, then land the full series arc into an episode map before any scene is written.
2. Write each episode from its map record plus the previous episode's exit state; persist every episode as its own screenplay file and keep the map as completion truth.
3. Review structure and continuity mechanically where tools exist; narrative quality and user acceptance remain separate evidence states.

<!-- contract:returns -->
## 6. Return, rework, and rollback

- If causality, character knowledge, or episode handoff fails, return to the earliest broken map record or scene before polishing prose.
- If the episode map conflicts with written episodes, the accepted map is revised explicitly or the conflict is escalated to the creator; episodes are not silently rewritten to match.

<!-- contract:review -->
## 7. Review gates

- [ ] Every episode produces a local dramatic result before its outgoing hook, and adjacent episodes hand off precise entry/exit states.
- [ ] Reveals, reversals, and payoffs trace to established facts; information releases match what their visible carriers support.
- [ ] An accepted rhythm profile is checked arithmetically only; a missing or proposed profile disables those checks honestly.
- [ ] Episode-map references resolve, every episode lands a local result before its hook, and adjacent episodes hand off precise states.
- [ ] Adaptation mappings preserve core character stances, relationships, and main line unless the creator accepted the change.

<!-- contract:pass -->
## 8. Pass standard and states

- The requested scope is written to disk: every planned episode has its own screenplay file, or the delivered excerpt is explicitly labeled as such.
- Continuation resumes from disk state without resetting episode numbering or accepted decisions.

> A pass below means this module's stated gates were met. Structural validity, real-task evidence, and user acceptance remain separate states.

<!-- contract:outputs -->
## 9. Outputs

- 项目开发/ creative brief, story engine, episode map, optional director brief, adaptation map, and project.json rhythm/pacing config.
- 剧集/<EP>/剧本.md single-episode Markdown screenplays with scene headings, dialogue, and production tags.

<!-- contract:boundaries -->
## 10. Boundaries, dependencies, and permissions

- These packages do not generate images, video, audio, or prompts, and do not perform asset splitting, storyboarding, or final review; downstream stages consume the written artifacts.
- They are adapted from the MIT-licensed drama-skills suite; upstream attribution is kept in each package LICENSE file.

<!-- contract:agents -->
## 11. Cross-Agent use

- The canonical package is the complete Skill folder, not a copied prompt fragment.
- `agents/openai.yaml` is optional Codex UI metadata and is not a runtime dependency for other hosts.
- Text-only work in any host that can read the complete folder; the bundled Python scripts need Python 3.9+ and are optional helpers, not creative judges.
- An Agent may read the instructions without native Skill discovery, but prompt-only reading must not be described as native integration.

<!-- contract:sources -->
## 12. Source files and references

**Runtime and metadata**

- [`agents/openai.yaml`](../../../skills/short-drama-develop/agents/openai.yaml)
- [`SKILL.md`](../../../skills/short-drama-develop/SKILL.md)

**References**

- [`references/adaptation-craft.md`](../../../skills/short-drama-develop/references/adaptation-craft.md)
- [`references/creative-reference-intake.md`](../../../skills/short-drama-develop/references/creative-reference-intake.md)
- [`references/director-brief-craft.md`](../../../skills/short-drama-develop/references/director-brief-craft.md)
- [`references/episode-design.md`](../../../skills/short-drama-develop/references/episode-design.md)
- [`references/genre-and-hook-playbook.md`](../../../skills/short-drama-develop/references/genre-and-hook-playbook.md)
- [`references/genre-cards.md`](../../../skills/short-drama-develop/references/genre-cards.md)
- [`references/genre-cards/亲子隐秘.md`](../../../skills/short-drama-develop/references/genre-cards/亲子隐秘.md)
- [`references/genre-cards/仙侠修真.md`](../../../skills/short-drama-develop/references/genre-cards/仙侠修真.md)
- [`references/genre-cards/动作任务.md`](../../../skills/short-drama-develop/references/genre-cards/动作任务.md)
- [`references/genre-cards/古装权谋.md`](../../../skills/short-drama-develop/references/genre-cards/古装权谋.md)
- [`references/genre-cards/复仇打脸.md`](../../../skills/short-drama-develop/references/genre-cards/复仇打脸.md)
- [`references/genre-cards/家庭关系.md`](../../../skills/short-drama-develop/references/genre-cards/家庭关系.md)
- [`references/genre-cards/悬疑规则.md`](../../../skills/short-drama-develop/references/genre-cards/悬疑规则.md)
- [`references/genre-cards/生活流.md`](../../../skills/short-drama-develop/references/genre-cards/生活流.md)
- [`references/genre-cards/破镜重圆.md`](../../../skills/short-drama-develop/references/genre-cards/破镜重圆.md)
- [`references/genre-cards/系统流.md`](../../../skills/short-drama-develop/references/genre-cards/系统流.md)
- [`references/genre-cards/职场喜剧.md`](../../../skills/short-drama-develop/references/genre-cards/职场喜剧.md)
- [`references/genre-cards/豪门婚恋.md`](../../../skills/short-drama-develop/references/genre-cards/豪门婚恋.md)
- [`references/genre-cards/身份错位.md`](../../../skills/short-drama-develop/references/genre-cards/身份错位.md)
- [`references/genre-cards/逆袭.md`](../../../skills/short-drama-develop/references/genre-cards/逆袭.md)
- [`references/genre-cards/重生穿越.md`](../../../skills/short-drama-develop/references/genre-cards/重生穿越.md)
- [`references/long-series-delivery.md`](../../../skills/short-drama-develop/references/long-series-delivery.md)
- [`references/mechanism-loop.md`](../../../skills/short-drama-develop/references/mechanism-loop.md)
- [`references/multi-episode-intake.md`](../../../skills/short-drama-develop/references/multi-episode-intake.md)
- [`references/premise-devices.md`](../../../skills/short-drama-develop/references/premise-devices.md)
- [`references/reveal-reversal-payoff.md`](../../../skills/short-drama-develop/references/reveal-reversal-payoff.md)
- [`references/serial-character-and-memory.md`](../../../skills/short-drama-develop/references/serial-character-and-memory.md)
- [`references/stage-contract.md`](../../../skills/short-drama-develop/references/stage-contract.md)
- [`references/story-craft.md`](../../../skills/short-drama-develop/references/story-craft.md)

**Deterministic helpers**

- [`scripts/episode_intake.py`](../../../skills/short-drama-develop/scripts/episode_intake.py)
- [`scripts/selftest.py`](../../../skills/short-drama-develop/scripts/selftest.py)

**Other packaged files**

- [`assets/creative-brief.md`](../../../skills/short-drama-develop/assets/creative-brief.md)
- [`assets/story-engine.md`](../../../skills/short-drama-develop/assets/story-engine.md)
- [`LICENSE`](../../../skills/short-drama-develop/LICENSE)
- [`templates/adaptation-map.example.jsonl`](../../../skills/short-drama-develop/templates/adaptation-map.example.jsonl)
- [`templates/episode-map.jsonl`](../../../skills/short-drama-develop/templates/episode-map.jsonl)
