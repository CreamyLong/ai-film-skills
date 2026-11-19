# Omni Rendered-Film Reviewer

| Status | New source package; structural checks and single-episode model calls only. No full-series acceptance evidence yet. |
|---|---|
| Can deliver alone | An evidence pack plus a severity-ranked review report; it does not generate, repair or rerender media. |
| Cannot claim alone | It cannot prove taste, performance, script causality, platform compliance or user acceptance; model findings need a human look at the cited frame or second. |

[Runtime `SKILL.md`](../../../skills/omni-review/SKILL.md) · [Install current source](../../INSTALLATION.md) · [Install](../../INSTALLATION.md) · [Compatibility](../../COMPATIBILITY.md) · [Design system](../../SKILL_DESIGN_SYSTEM.md)

No release snapshot yet; install from the current source tree.

<!-- contract:purpose -->
## 1. Purpose

Judge a rendered AI drama episode with a multimodal reviewer: identity, burned-in text, spatial continuity, cut-point sound, artifacts and sequence clarity, with frame- or second-level evidence.

<!-- contract:principles -->
## 2. Design principles

- The final, watchable video is the outcome; prompts, clips, edit projects, and QC reports are intermediate artifacts.
- Preserve locked source facts and review the whole final render, not isolated attractive frames.
- Repair the earliest point where the audience loses trust and distinguish candidate from qualified delivery.

<!-- contract:standalone -->
## 3. Standalone scope

Use this module by itself when the requested result stays inside the following boundary:

An evidence pack plus a severity-ranked review report; it does not generate, repair or rerender media.

**Cannot claim alone:** It cannot prove taste, performance, script causality, platform compliance or user acceptance; model findings need a human look at the cited frame or second.

<!-- contract:inputs -->
## 4. Inputs

- Current approved script, assets, visual rules, decisions, checkpoints, delivery format, and qualification definition.
- Explicit authority for paid generation, external services, music, voices, publishing, or other consequential actions.
- A choice between autonomous production and user-directed execution when existing storyboards or structures are locked.

<!-- contract:workflow -->
## 5. Workflow

1. Enter only for actual video work. Preserve approved decisions; check spend, rights and change scope, editable coverage, performance-based take selection, picture lock, sound turnovers, real color management and target-specific mastering. Load only applicable contracts.
2. Preserve the selected shot design and use this package's own compiler; no companion Skill is required.
3. Choose a generation route, create genuine motion, edit, build sound, and render the real final file.
4. Watch the whole render at least twice: once for story/emotion, once for technical and continuity defects.
5. Repair blocking failures and deliver with the honest status `qualified`, `candidate`, or `unfinished/needs validation`.
6. Build evidence from the editlist, prompts and rendered file before calling the model: per-scene grids, reference-to-frame identity pairs and cut-point audio pairs.
7. Run cheap tiers first, send audio in A/B pairs, and keep the model output as review_required until a human confirms the cited evidence.

<!-- contract:returns -->
## 6. Return, rework, and rollback

- Return to the earliest wrong layer: script/directing, shot design, prompt, source clip, edit, sound, or final render.
- A platform task success, valid duration, or good still frame cannot bypass full-playback review.
- User-locked storyboards remain locked unless revision authority is explicit.

<!-- contract:review -->
## 7. Review gates

- [ ] Check applicable story, shot, asset, edit, sound and delivery gates. Required detector failures or missing measurements block delivery; the 100-point pre-generation rubric has frozen regression/control thresholds. Structural checks never prove full playback, rights or user acceptance.
- [ ] The actual final file opens and has been watched from beginning to end; no hidden replacement file is reviewed instead.
- [ ] Rights, costs, permissions, and unresolved limitations are explicit.
- [ ] Every finding names a shot or timecode, an observable difference and one repair owner; unsupported findings are recorded as false positives.
- [ ] A blocker count above zero keeps the cut at candidate status; model silence never counts as a pass.

<!-- contract:pass -->
## 8. Pass standard and states

- Only a fully watched render that passes every applicable hard gate may be called a qualified final video.
- Anything missing a key gate remains candidate or unfinished even when files and project artifacts exist.

> A pass below means this module's stated gates were met. Structural validity, real-task evidence, and user acceptance remain separate states.

<!-- contract:outputs -->
## 9. Outputs

- The actual playable film, single shot or video test requested, with its verified scope and status.
- Only the necessary supporting artifacts and a concise record of review, repairs, rights, and remaining limits.

<!-- contract:boundaries -->
## 10. Boundaries, dependencies, and permissions

- Do not write or run scripts to batch-generate prompts through template loops, substitution, concatenation or model calls. Author and review each complete prompt individually; scripts may only validate or preserve completed text unchanged. Compilation, later polishing and batch requests grant no exception.
- Installing this method does not grant video models, paid credits, music rights, voice rights, or publishing authority.
- Never describe a storyboard, prompt, generated clip, edit timeline, or unreviewed render as the finished film.
- Creative ideas, workflow tests and requests to see text-stage results do not authorize generation; a single-shot video test stays within its explicit scope.

<!-- contract:agents -->
## 11. Cross-Agent use

- The canonical package is the complete Skill folder, not a copied prompt fragment.
- `agents/openai.yaml` is optional Codex UI metadata and is not a runtime dependency for other hosts.
- Real production requires media-generation tools, editing and audio capabilities, file access, sufficient permissions or budget, and full-playback review. A text-only host can inspect the method but cannot claim a finished video.
- An Agent may read the instructions without native Skill discovery, but prompt-only reading must not be described as native integration.

<!-- contract:sources -->
## 12. Source files and references

**Runtime and metadata**

- [`agents/openai.yaml`](../../../skills/omni-review/agents/openai.yaml)
- [`SKILL.md`](../../../skills/omni-review/SKILL.md)

**References**

- [`references/model-behavior.md`](../../../skills/omni-review/references/model-behavior.md)
- [`references/qwen-mm-plugins.md`](../../../skills/omni-review/references/qwen-mm-plugins.md)
- [`references/repair-matrix.md`](../../../skills/omni-review/references/repair-matrix.md)
- [`references/review-tiers.md`](../../../skills/omni-review/references/review-tiers.md)
- [`references/seam-review.md`](../../../skills/omni-review/references/seam-review.md)
- [`references/verdict-schema.md`](../../../skills/omni-review/references/verdict-schema.md)

**Deterministic helpers**

- [`scripts/episode_audit.py`](../../../skills/omni-review/scripts/episode_audit.py)
- [`scripts/omni_review.py`](../../../skills/omni-review/scripts/omni_review.py)
- [`scripts/repair_plan.py`](../../../skills/omni-review/scripts/repair_plan.py)
- [`scripts/seam_review.py`](../../../skills/omni-review/scripts/seam_review.py)

**Other packaged files**

- [`LICENSE`](../../../skills/omni-review/LICENSE)
