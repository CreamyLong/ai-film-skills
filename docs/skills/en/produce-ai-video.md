# produce-ai-video — qualified final video production

| Status | Current source is an isolated overhaul candidate; installation history and user acceptance are separate. |
|---|---|
| Can deliver alone | A full production and validation contract; with the required host tools and permissions, an actual reviewed final video. |
| Cannot claim alone | Installing the Skill alone does not supply models, credits, rights, editing tools, or a qualified video. |

[Runtime `SKILL.md`](../../../skills/produce-ai-video/SKILL.md) · [ai-storyboard-director-v5.8.6 ZIP](https://github.com/62656456/ai-film-skills/releases/download/ai-storyboard-director-v5.8.6/produce-ai-video.zip) · [Install](../../INSTALLATION.md) · [Compatibility](../../COMPATIBILITY.md) · [Design system](../../SKILL_DESIGN_SYSTEM.md)

This release snapshot aligns the Storyboard 5.8.6 prompt contract and its production handoffs. Historical archives keep their original contents.

<!-- contract:purpose -->
## 1. Purpose

Turn an approved script or passage into a qualified, watchable AI-generated final video through directing, shots, generation, edit, sound, full playback, and repair.

<!-- contract:principles -->
## 2. Design principles

- The final, watchable video is the outcome; prompts, clips, edit projects, and QC reports are intermediate artifacts.
- Preserve locked source facts and review the whole final render, not isolated attractive frames.
- Repair the earliest point where the audience loses trust and distinguish candidate from qualified delivery.

<!-- contract:standalone -->
## 3. Standalone scope

Use this module by itself when the requested result stays inside the following boundary:

A full production and validation contract; with the required host tools and permissions, an actual reviewed final video.

**Cannot claim alone:** Installing the Skill alone does not supply models, credits, rights, editing tools, or a qualified video.

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
6. Preserve the selected photography in the current six-module order with visual style second and an unnumbered negative prompt at the end. Keep professional optical names together with their visible action.
7. Before each actual video-model submission, review the exact payload, approved assets and relevant story and episode handoffs; repair or stop on unresolved hard requirements, then review actual media and affected boundaries.
8. Record prompt compilation scope, additions, fallback and reference bindings; compare local preflight hashes while retaining independent semantic and keyframe review.
9. When the target runtime accepts the official H3 Context-IR format, compile through the six-section structure with semantic Subject labels, retention markers, shot times and dialogue tags, declare prompt_format in the payload, and run the structural checker; structure alone never proves semantic, media or continuity approval.
10. When the target runtime runs an H3 base mode (t2va/i2va/fl2va/l2va), compile through the official three-field structure with the mode's alignment instruction, shot times and dialogue tags, declare prompt_format "h3_base" with h3_mode in the payload, and run the structural checker; structure alone never proves semantic, media or continuity approval.
11. For other providers, translate the same director decisions into the venue's verified prompt dialect — one shell per prompt, unverified dialects stay marked unverified — and record prompt_format and provider identity in the submission record.
12. When the runtime is ComfyUI with the MiniMax H3 TimelineDirector plugin, choose its node path, task recipe, video reference mode, audio route, segment overlaps and quality parameters from the runtime adapter, and run the timeline plan checker on the actual timeline_data; it mirrors per-segment labels, guides and the final soundtrack route and blocks inputs the plugin would silently drop, renumber, lock or mute.
13. Run mechanical media QC (streams, duration, resolution, frame rate, black and frozen frames, audio level and loudness, subtitle cue coverage, contact-sheet evidence) on every generated segment and the assembled cut; measurements are evidence, not approval.
14. Assemble and deliver through a derived EDL, seam verification, subtitle-to-dialogue coverage, loudness and spec checks, and a delivery manifest; every failure returns to the earliest owning layer.
15. Register every video-model submission, its dependencies, reviews and outcome in the production ledger; reserve before sending, reconcile unknown outcomes before any resubmission, and invalidate downstream items when an upstream file or review changes.

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
- [ ] Ledger reviews record explicit user or delegated authority with evidence hashes; registration, hash and gateway checks are structural only and never replace semantic, visual, audio or continuity review.
- [ ] Character multi-view, matching location views, applicable props and voice rights are prepared; continuity and prompt evidence are checked for the current scope, with missing evidence marked unverified.

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

- [`agents/openai.yaml`](../../../skills/produce-ai-video/agents/openai.yaml)
- [`SKILL.md`](../../../skills/produce-ai-video/SKILL.md)

**References**

- [`references/audio-dubbing-post.md`](../../../skills/produce-ai-video/references/audio-dubbing-post.md)
- [`references/autonomous-production-workflow.md`](../../../skills/produce-ai-video/references/autonomous-production-workflow.md)
- [`references/context-ir-format.md`](../../../skills/produce-ai-video/references/context-ir-format.md)
- [`references/editorial-workflow.md`](../../../skills/produce-ai-video/references/editorial-workflow.md)
- [`references/finishing-and-delivery.md`](../../../skills/produce-ai-video/references/finishing-and-delivery.md)
- [`references/h3-base-format.md`](../../../skills/produce-ai-video/references/h3-base-format.md)
- [`references/h3-timeline-director.md`](../../../skills/produce-ai-video/references/h3-timeline-director.md)
- [`references/keyframe-visual-review.md`](../../../skills/produce-ai-video/references/keyframe-visual-review.md)
- [`references/pregeneration-quality-gate.md`](../../../skills/produce-ai-video/references/pregeneration-quality-gate.md)
- [`references/production-controls.md`](../../../skills/produce-ai-video/references/production-controls.md)
- [`references/production-ledger.md`](../../../skills/produce-ai-video/references/production-ledger.md)
- [`references/production-validation.md`](../../../skills/produce-ai-video/references/production-validation.md)
- [`references/prompt-compilation-preflight.md`](../../../skills/produce-ai-video/references/prompt-compilation-preflight.md)
- [`references/provider-shells.md`](../../../skills/produce-ai-video/references/provider-shells.md)
- [`references/qualified-video-acceptance.md`](../../../skills/produce-ai-video/references/qualified-video-acceptance.md)
- [`references/release-assembly.md`](../../../skills/produce-ai-video/references/release-assembly.md)
- [`references/segment-seam-continuity.md`](../../../skills/produce-ai-video/references/segment-seam-continuity.md)
- [`references/shot-audit-protocol.md`](../../../skills/produce-ai-video/references/shot-audit-protocol.md)
- [`references/spatial-consistency-ledger.md`](../../../skills/produce-ai-video/references/spatial-consistency-ledger.md)
- [`references/storyboard-prompt-compiler.md`](../../../skills/produce-ai-video/references/storyboard-prompt-compiler.md)
- [`references/submission-preflight.md`](../../../skills/produce-ai-video/references/submission-preflight.md)

**Deterministic helpers**

- [`scripts/context_ir_check.py`](../../../skills/produce-ai-video/scripts/context_ir_check.py)
- [`scripts/h3_base_check.py`](../../../skills/produce-ai-video/scripts/h3_base_check.py)
- [`scripts/media_qc.py`](../../../skills/produce-ai-video/scripts/media_qc.py)
- [`scripts/production_state.py`](../../../skills/produce-ai-video/scripts/production_state.py)
- [`scripts/prompt_preflight.py`](../../../skills/produce-ai-video/scripts/prompt_preflight.py)
- [`scripts/quality_gate_check.py`](../../../skills/produce-ai-video/scripts/quality_gate_check.py)
- [`scripts/shot_preflight.py`](../../../skills/produce-ai-video/scripts/shot_preflight.py)
- [`scripts/submission_gateway.py`](../../../skills/produce-ai-video/scripts/submission_gateway.py)
- [`scripts/timeline_plan_check.py`](../../../skills/produce-ai-video/scripts/timeline_plan_check.py)

**Distribution notices in new ZIP builds**

New builds attach these files inside the Skill folder without editing its runtime source. Historical release archives are unchanged.

- [`LICENSE`](../../../LICENSE)
