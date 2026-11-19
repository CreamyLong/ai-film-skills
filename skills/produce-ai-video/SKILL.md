---
name: produce-ai-video
description: Produce or revise an actual playable AI video when the user explicitly requests video generation, an actual video test, or a finished film. Interpret the story, preserve locked directing and storyboard decisions, then generate, edit, add authorized sound, review playback, and repair within scope. Use the verified prompt format and execution checks for the selected runtime. Creative shot ideas, workflow or Skill testing, storyboards, prompts, and requests for results within those text stages do not activate video production.
---

# Produce AI Video

## 提示词逐项创作硬规则

- 禁止编写或运行批量生成提示词的脚本，包括 Python/Shell/JS、循环套模板、变量替换、片段拼接、批量调用模型或其他自动化流程。图片、资产、分镜、视频的正向与负向提示词均适用；用户要求多条或全片提示词也不构成例外。
- 必须依据当前剧本、已定设计与每个资产/镜头的具体关系，逐项理解、逐项撰写、逐项复核完整正文。模板仅供组织表达；“编译”指逐项转写已定决定，不授权程序代写。
- 脚本仅可校验、编号、索引、计算哈希、原样保存或封装已经逐项完成并复核的完整正文；不得生成、补写、改写或拼装提示词正文。已授权的图片/视频批量执行仍须使用这些完成稿并通过相应质量门。
- 不能以逐条循环、拆成多个单次脚本、改称编译器或先批量生成再人工润色绕过。发现脚本批量产出的提示词时，不得交付或提交生成，须回到源材料逐项重新撰写和复核。

## Outcome

Deliver the actual video artifact the user requested. A finished-film request needs an assembled film; an explicitly requested single-shot video or video test stays within that scope. Storyboards, prompts and QC reports are supporting artifacts, not proof of video delivery.

## Entry and handoff

Read the latest request in its current stage. “Test”, “show the result”, or a film example does not by itself authorize media generation. Creative shot ideas stay as optional text describing the intended image, story purpose, camera or edit, and tradeoffs. They do not require an account, credits, reference upload or a playable sample. Adopting an idea authorizes only the adoption named by the user, not a subsequent generation step.

Start this workflow only for an actual video request or an already authorized video task. Use its current director plan, storyboard, approved assets and entry/exit states as the handoff. Complete only missing decisions needed for execution; do not rerun every upstream Skill or redesign locked shots. New creative alternatives remain separate suggestions until specifically adopted; do not add them to the production queue.

This package contains its own production storyboard and six-module prompt compiler in `references/storyboard-prompt-compiler.md`. Use it only after the director judgment is complete.

## Production controls by task

Load only applicable guidance and reuse valid decisions:

| Task | Local contract |
|---|---|
| Actual production, spend, rights or upstream changes | `references/production-controls.md`; record limits and dependencies, do not claim unimplemented budget or rights enforcement |
| Coverage before generation, take selection, scene/full-cut development, picture lock | `references/editorial-workflow.md`; protect listening and performance, classify seams, distinguish edit freedom from locked execution |
| Image repair, shot matching, color management, mastering or delivery | `references/finishing-and-delivery.md`; inspect real signal and target requirements, never infer HDR/Log from a prompt |
| Claims of reliable production or an explicit real-media validation task | `references/production-validation.md`; maintenance is not media authorization and written contracts are not completed real-film evidence |

## Choose the execution mode

### Autonomous production mode

Use this mode when the user asks for an actual video or film and delegates the necessary directing and production decisions. A test of Skill instructions or creative thinking alone is not this mode.

- Read the project knowledge, current script, approved assets, visual rules, decisions, and checkpoints.
- Make the director decisions independently.
- Design the shot groups, prompts, production route, generation, selection, edit, sound, review, and repairs.
- Do not push ordinary directing decisions back to the user.
- Ask only when a missing choice materially changes story meaning, spend, permissions, publication, or an already locked structure.

### User-directed execution mode

Use this mode when the user supplies or has repeatedly adjusted a storyboard, timing, shot order, staging, dialogue, or prompt structure.

- Treat the user-locked structure as authoritative.
- Change only the requested scope.
- Do not add shots, remove shots, reorder beats, rewrite dialogue, or replace staging in the name of optimization.
- If a requested result conflicts with the locked structure, identify the exact conflict and its visible consequence before proposing a change.

## Run the autonomous workflow

1. **Lock sources and acceptance.** Identify the unique project, current script version, approved assets, fixed decisions, requested video scope, permissions, cost boundary, and relevant acceptance checks. Reuse verified, unchanged context; a local correction reads the affected material and required continuity, not the whole project again. Separate verified facts, unknowns, assumptions, and conventions. Before keyframe work, audit the applicable character, location and prop assets using [submission-preflight.md](references/submission-preflight.md); missing prerequisites stop keyframe work at asset completion, not text-only prompt delivery.
2. **Interpret the script.** Determine the dramatic event, character objective, power relation, information reveal, physical action, emotional turn, sound cue, entry state, and exit state. Read [autonomous-production-workflow.md](references/autonomous-production-workflow.md) for the auditable decision framework.
3. **Direct before prompting.** Decide what the audience must see and in what order. Build a world-state model for space, subjects, props, light sources, movement axes, and continuity. Read [spatial-consistency-ledger.md](references/spatial-consistency-ledger.md) when locking multi-character scenes, reversible props, or cross-segment entrances.
4. **Design segments and shots.** Treat a segment as a dramatic sequence and a shot as one uninterrupted viewpoint. Choose continuous staging, cuts or a mixed structure from performance, viewing order and spatial relations; there is no minimum shot count, mandatory wide opening, shot-size ladder or fixed duration grid. Every cut serves the audience's understanding or experience. Working shot size is an optional diagnostic, not a rule overriding the selected staging or edit.
5. **Create and compile the director package.** Produce a `DIRECTOR_SHOT_PACKAGE` containing the segment objective, entry and exit states, world-state lock, shot order, timing, framing, camera, visible action, sound, cut motivation, and continuity handoff. Only after this package is coherent may `references/storyboard-prompt-compiler.md` convert it into the approved five-column storyboard and six-module video prompt. When the actual target runtime accepts the official H3 Context-IR full-reference format, compile the same director package through [context-ir-format.md](references/context-ir-format.md) instead: it adds semantic `<Subject N>` definitions, per-label retention declarations, `[Shot N]` cut times and `<d>` dialogue tags; it is a different prompt structure, not an upgrade of the six-module text, and the choice is recorded in the preflight payload's `prompt_format`. When the target runtime instead runs an H3 base mode (text-, first-frame-, first-and-last-frame- or last-frame-to-video without per-label reference tracking), compile through [h3-base-format.md](references/h3-base-format.md): it keeps `[Shot N]`, `(Sx)` and `<d>` markers but drops `subject_definitions` and `retention_analysis`, adds the mode's first-line alignment instruction, and records `prompt_format: "h3_base"` with `h3_mode`. For any other provider, read [provider-shells.md](references/provider-shells.md): the same director decisions are translated into that venue's verified dialect, one shell per prompt, and unverified dialects stay marked `unverified` rather than pretending an H3-shaped prompt fits.
6. **Choose the production route.** Preserve the director timing and shot design. If one model call cannot reliably render the required internal shots, generate individual shots or smaller clusters and edit them into the designed segment. Never let a model's maximum duration redefine the dramatic timing. Before fixing cut points, read [transition-causality.md](references/transition-causality.md) for each boundary's motive, continuity anchor and audio plan. For ComfyUI with the MiniMax H3 TimelineDirector plugin, use [h3-timeline-director.md](references/h3-timeline-director.md) to choose its node path, reference and audio routes, overlap, and quality parameters, then run `scripts/timeline_plan_check.py` on the actual `timeline_data`. Use the Planner → FiniteSegmentSampler path for one continuous action spanning multiple generation windows with positive overlap. Use the verified native shot cuts within a single generation or edit separately generated shots. A long episode, multiple identities or reference audio alone does not require positive-overlap segmentation. Select H3 base only when the verified mode supports the shot and its references.
7. **Preflight each submission, then generate real motion.** Write and check the scene-first plan with [scene-production-plan.md](references/scene-production-plan.md) and `scripts/scene_plan_check.py`. Reject missing environment references, invalid off-screen speech and missing visible-speech audio routes. Review each keyframe before it feeds motion generation using [keyframe-visual-review.md](references/keyframe-visual-review.md). Pass the [pregeneration-quality-gate.md](references/pregeneration-quality-gate.md) fixture gate before batch generation.
   - **Every provider and retry:** Before every video-model submission, including retries, audit the exact prompt, attachments, asset versions and continuity using [submission-preflight.md](references/submission-preflight.md), `scripts/shot_preflight.py` and `scripts/prompt_preflight.py`. Inspect both reports and match their prompt hashes to the actual payload. Resolve every applicable hard finding. Register the exact request and dependencies, verify and reserve it at the actual send boundary, and bind the provider's job receipt and result to that attempt per [production-ledger.md](references/production-ledger.md). Stop when the chosen runtime cannot verify a required binding or execution step. Reconcile unknown outcomes before retrying.
   - **Prompt format:** Apply [h3-official-prompt-contract.md](references/h3-official-prompt-contract.md) and `scripts/context_ir_check.py` only to H3 Ref2VA (`prompt_format: "context_ir"`). For H3 base, declare `prompt_format: "h3_base"` with `h3_mode` and use `scripts/h3_base_check.py`. The respective structure check also runs standalone when there is only prompt text. For other routes, use their verified [provider dialect](references/provider-shells.md), with no H3 tags or H3 wording bans imposed as universal requirements.
   - **Execution runtime:** Use the shipped `scripts/submission_gateway.py` only with a graph it supports on ComfyUI MiniMax H3 TimelineDirector. For other graphs or providers, use a verified runtime adapter that enforces the same ledger and request checks. The adapter supplies its own job ID, receipt and cancellation capabilities. Only on ComfyUI, read back the queued graph, compare prompt, actual attachments, seed, step and frame parameters, and output prefix, and cancel mismatched or superseded pending work by `prompt_id`. For every route, hold mismatched or unverified output and reconcile the job before retrying. A direct call that bypasses the checks does not satisfy this gate.
   - **Speech, captions and output:** Verify the planned speech route with `scripts/speech_route_check.py`. Use `scripts/caption_preflight.py` and its H3-specific wording blocks for H3 prompts; other providers use their verified prompt and caption requirements. Produce real motion, not keyframe slideshows. After rendering, extract caption evidence with `scripts/caption_frame_qc.py` and require the matching reviewed report in `scripts/media_qc.py --caption-report <report> --require-caption-review` for delivery. Compare the ASR to the planned lines with `scripts/dialogue_content_check.py`; block unrelated or missing dialogue and resolve reported mismatches by listening to the audio. Run `scripts/audio_continuity_check.py` before assembly and with `--video` after assembly per [audio-continuity.md](references/audio-continuity.md). When authorized, use [multimodal-review.md](references/multimodal-review.md) for evidence-based triage of identity, burned-in text, space, camera motion and audio cuts.
8. **Select and assemble.** Judge takes by performance, identity, action, continuity, composition, and editability. Cut on motivated action, gaze, occlusion, object, sound, or information change. Add handles where the tool permits; do not concatenate fixed clip durations blindly. When segments are generated independently and spliced, read [segment-seam-continuity.md](references/segment-seam-continuity.md) before scheduling generation: anchor each seam on the real captured last frame, never a redrawn still. After each shot or scene clip is rendered, run `scripts/auto_review.py` and read its JSON verdict; `block` stops that scene from entering assembly, `review`/`error` requires a human look, and a `pass` never replaces full playback. The trigger, protocol and cost are in [auto-review-gate.md](references/auto-review-gate.md). Before any concat, run `scripts/ffmpeg_conform_check.py` on every clip and conform resolution, SAR, pixel format, frame rate, color tags, sample rate and channel layout to one target; read [ffmpeg-assembly-toolkit.md](references/ffmpeg-assembly-toolkit.md) for the parameter contract, hard-cut rule, audio-only 2–3 frame crossfade, loudness, subtitle burn and atomic delivery. Never cross-dissolve between shots; never repeat dialogue to hide a seam.
9. **Build sound.** Integrate dialogue, performance breaths, environment, effects, transitions, silence, and music only when authorized. Make sound carry space, action, rhythm, and continuity rather than feeling pasted on. Read [audio-dubbing-post.md](references/audio-dubbing-post.md) for native-audio selection, authorized dubbing, sound editorial, stems and mixing; usable native audio is not automatically replaced or stacked with duplicate dialogue.
10. **Watch, repair, and rewatch.** Run `scripts/media_qc.py` and the checks in [ffmpeg-assembly-toolkit.md](references/ffmpeg-assembly-toolkit.md) on every generated segment and on the assembled cut for the mechanical checks (streams, duration, resolution, frame rate, black and frozen frames, audio level and loudness, subtitle cue coverage, optional contact-sheet evidence); mechanical results are measurements, not approval. Review generated segments and their actual boundaries, then the entire film at normal speed for story and rhythm; inspect continuity, artifacts and sound as directed by [submission-preflight.md](references/submission-preflight.md). Keep the last checked assembly before changing it. Fix the earliest responsible defect within the authorized generation/cost boundary, recheck the affected material and watch the final assembly. If a repair fails, restore the previous checked assembly; service failure, exhausted budget or missing evidence stops the loop with an honest incomplete result. Rejected media remains traceable; when disk cleanup is needed, follow [asset-retention-and-cleanup.md](references/asset-retention-and-cleanup.md): retain a fallback, dry-run the manifest, protect every referenced file, and obtain explicit approval for that batch before deletion. Use [qualified-video-acceptance.md](references/qualified-video-acceptance.md).
11. **Deliver honestly.** Assemble and deliver per [release-assembly.md](references/release-assembly.md) and the applicable finishing contract: bind the approved picture lock, final sound and requested subtitle versions, verify the target specifications, and record files, hashes, QC results and residual risk. Return the playable final video, its duration and format, the validation state, and any visible residual risk. If full-playback review or a hard gate is unavailable, report `未完成/待验证`; never call the result qualified.

## Enforce hard rules

- Every shot must pass a physical-plausibility gate before it enters the edit: object scale against the human body, support and contact, finger/joint and hinge/wheel structure, duplicates and reflections, shadow direction, floating or interpenetrating props. An anti-physical shot is rejected, not repaired in post: redo the keyframe/asset first if the static reference is wrong, or rerun the shot with fixed action/contact wording and a new seed; information-bearing props move to a real still plate.
- Every character in the task requires its locked four-image character asset on a white background (full-body hero image, face close-up, 3x3 expression grid, and a turnaround sheet with front, 90-degree side and back full-body views plus six head angles) and a detail plate for every identity mark visible in the planned shots, before keyframe generation. A missing character asset stops the batch; do not improvise a character's identity from a single portrait or one good keyframe.
- Every actual video-model call, including a retry, requires a ready ledger record of its exact request. An `unknown` prior attempt must be reconciled before any resubmission; a `failed` one may be retried only as a newly reserved attempt. See [production-ledger.md](references/production-ledger.md).
- Every actual video-model call, including a retry, requires a fresh preflight of its exact payload and affected dependencies. Neither a text-only request nor a preflight pass authorizes generation, spending, uploads, voice cloning or publication.
- Do not start from prompt formatting. Start from what the audience must see.
- Do not equate a script paragraph, generation segment, and shot.
- Do not equate continuity with a fixed camera. Keep the world state fixed while recalculating screen projection after every camera change.
- Carry the selected audience information, environment activity and sound through compilation. Places keep operating during protagonist action; deliberate quiet and stable light remain valid. Do not add weather, crowds or plot sounds during compilation to fill fields.
- Do not count repeated crops, cosmetic zooms, or unchanged viewpoints as new effective shots.
- Do not declare success because files exist, durations match, prompts are complete, or individual clips pass technical checks.
- Do not deliver autonomous work that resembles independent single-shot demonstrations joined together.
- Do not claim a qualified final video without actually viewing the complete rendered file.

## Output Contract

Keep internal work concise and production-facing. The user-facing completion must lead with the playable video and one of these states:

- `合格成片`: every hard gate passed after full playback.
- `候选成片`: playable, but one or more visible quality judgments still await user review.
- `未完成/待验证`: generation, assembly, full playback, or a hard gate is incomplete.

Never substitute text, stills or a QC checklist for a requested video. A test clip fulfills an explicitly requested video-test scope; it does not prove an entire film or Skill has passed user acceptance. Explain the verified scope, and preserve user approval as a separate decision.
