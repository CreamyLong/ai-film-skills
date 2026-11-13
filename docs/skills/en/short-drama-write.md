# short-drama-write — single-episode screenplay

| Status | Adapted from the MIT drama-skills suite; structural checks and self-tests only, no real-task or user-acceptance evidence yet. |
|---|---|
| Can deliver alone | Episode screenwriting package with deterministic index and duration-estimate scripts; reads the development package's accepted artifacts when present but also works from a bare outline. |
| Cannot claim alone | It does not split assets, write storyboards or media prompts, generate media, set the project rhythm profile, or issue final review verdicts. |

[Runtime `SKILL.md`](../../../skills/short-drama-write/SKILL.md) · [Install current source](../../INSTALLATION.md) · [Install](../../INSTALLATION.md) · [Compatibility](../../COMPATIBILITY.md) · [Design system](../../SKILL_DESIGN_SYSTEM.md)

No release snapshot yet; install from the current source tree. MIT license retained in package LICENSE.

<!-- contract:purpose -->
## 1. Purpose

Write or revise shootable Chinese short-drama/comic-drama episode Markdown screenplays, one episode at a time or as a series batch, preserving author text and normalizing production tags.

<!-- contract:principles -->
## 2. Design principles

- Build series story from causality, character state, and precise handoff facts before any production contract; a premise, outline, or episode map is not a substitute for the requested full script.
- Separate creator-proposed values from creator-accepted facts; inferred settings are marked as inferred and confirmed before they harden into canon.
- Genre cards, hook patterns, and rhythm profiles are optional calibrated aids, never mandatory templates or quality proof.
- Every scene must change information, power, relationship, emotion, physical state, or risk; scenes without change are cut or merged.
- Dialogue carries agenda and subtext rather than explanation; creator-supplied text is preserved and never trimmed under style rules.

<!-- contract:standalone -->
## 3. Standalone scope

Use this module by itself when the requested result stays inside the following boundary:

Episode screenwriting package with deterministic index and duration-estimate scripts; reads the development package's accepted artifacts when present but also works from a bare outline.

**Cannot claim alone:** It does not split assets, write storyboards or media prompts, generate media, set the project rhythm profile, or issue final review verdicts.

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
- [ ] Exit state hands off the six facts: who is where doing what, who knows what, key props, relationship/power shifts, and irreversible actions.
- [ ] The first beat stands alone as a hook; an accepted rhythm profile is checked arithmetically, never enforced as a beat template.

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

- [`agents/openai.yaml`](../../../skills/short-drama-write/agents/openai.yaml)
- [`SKILL.md`](../../../skills/short-drama-write/SKILL.md)

**References**

- [`references/dialogue-craft.md`](../../../skills/short-drama-write/references/dialogue-craft.md)
- [`references/production-format-dialect.md`](../../../skills/short-drama-write/references/production-format-dialect.md)
- [`references/scene-handoff-capsule.md`](../../../skills/short-drama-write/references/scene-handoff-capsule.md)
- [`references/scene-sound-dramaturgy.md`](../../../skills/short-drama-write/references/scene-sound-dramaturgy.md)
- [`references/screenplay-format.md`](../../../skills/short-drama-write/references/screenplay-format.md)
- [`references/script-craft.md`](../../../skills/short-drama-write/references/script-craft.md)
- [`references/stage-contract.md`](../../../skills/short-drama-write/references/stage-contract.md)
- [`references/substitutable-realization.md`](../../../skills/short-drama-write/references/substitutable-realization.md)
- [`references/text-defect-checklist.md`](../../../skills/short-drama-write/references/text-defect-checklist.md)

**Deterministic helpers**

- [`scripts/duration_estimate.py`](../../../skills/short-drama-write/scripts/duration_estimate.py)
- [`scripts/screenplay_index.py`](../../../skills/short-drama-write/scripts/screenplay_index.py)
- [`scripts/selftest.py`](../../../skills/short-drama-write/scripts/selftest.py)

**Other packaged files**

- [`assets/screenplay.md`](../../../skills/short-drama-write/assets/screenplay.md)
- [`LICENSE`](../../../skills/short-drama-write/LICENSE)
