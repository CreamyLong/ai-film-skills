---
name: film-production-orchestrator
description: Unified entry for AI film creation and repair when the user does not know which Skill to choose. Turn a sentence, story, reference video, music or product material into a scoped workflow for short drama, TVC, promotional video, MV or product film. Plan prerequisites, coordinate available specialist roles through the host, inspect handoff evidence and continue to the requested deliverable. Also triage production defects. Text-only requests never authorize media generation; unavailable tools or delegation are reported, not simulated.
---

# Film Production Orchestrator | 影视创作总控

## 提示词逐项创作硬规则

- 禁止编写或运行批量生成提示词的脚本，包括 Python/Shell/JS、循环套模板、变量替换、片段拼接、批量调用模型或其他自动化流程。图片、资产、分镜、视频的正向与负向提示词均适用；用户要求多条或全片提示词也不构成例外。
- 必须依据当前剧本、已定设计与每个资产/镜头的具体关系，逐项理解、逐项撰写、逐项复核完整正文。模板仅供组织表达；“编译”指逐项转写已定决定，不授权程序代写。
- 脚本仅可校验、编号、索引、计算哈希、原样保存或封装已经逐项完成并复核的完整正文；不得生成、补写、改写或拼装提示词正文。已授权的图片/视频批量执行仍须使用这些完成稿并通过相应质量门。
- 不能以逐条循环、拆成多个单次脚本、改称编译器或先批量生成再人工润色绕过。发现脚本批量产出的提示词时，不得交付或提交生成，须回到源材料逐项重新撰写和复核。

本入口将上述硬规则传给每个任务包；专业角色逐项创作提示词。总控不以脚本或批量模型调用代替创作，也不因负责调度便获得媒体、费用或批准权限。

## Outcome

Accept the user's goal without requiring them to select Skills. Own scope, prerequisites, task order, handoffs, progress and the requested endpoint; specialist roles own creative and production decisions. Use actual host capabilities to continue the work, not just recommend a list of Skills. A plan is not execution, a returned file is not approval, and a routing decision is not a repair.

## Choose the mode and load only its guidance

| Mode | Trigger and local guidance |
|---|---|
| Creation orchestration / 创作总控 | A goal, idea, reference video, song or product input; read `references/creation-workflows.md` for the applicable task, then `references/orchestration-loop.md` |
| Problem triage / 问题分诊 | A defect, failed artifact or uncertainty about who should repair it; use the triage rules below and `references/routing-cases.md`; read the loop when repair execution is requested |
| Direct stage request | Preserve the requested artifact and stage, assign its owner and continue if supported; no unnecessary full-project planning or upstream restart |

Do not treat "which Skill?", maintenance, an example film, accepting a creative idea, or "continue" as new media authorization. A finished-video request can include necessary intermediate production only within its confirmed scope, spend and permissions. Storyboard, prompt and proposal requests stop at their own endpoint.

## Run the orchestration loop

1. Recover the actual project, supplied sources, requested endpoint, valid approvals and existing progress. Separate facts, assumptions, unknowns and user locks; reuse unchanged work.
2. Identify the task type and acceptance criteria. Make ordinary creative/production choices through the owning role; ask only when a missing choice materially changes meaning, brand/product truth, locked structure, rights, publication or spend.
3. Check actual input-reading, image/video/audio, editing, playback and delegation capabilities. Resolve role codes using the host's actually discovered capabilities; do not invent available tools or installed Skills.
4. Form only the required tasks, dependencies, asset needs and review gates. Detect people, spaces, products/props, voices, music and historical/state variants; reconcile source, design and actual submission inventories.
5. Dispatch ready tasks through supported host mechanisms within authorization. Do not stop at a routing table when execution is available and requested. If dispatch is unavailable, return executable task packages and the exact blocked capability; standalone planning still works, but no downstream work is claimed.
6. Inspect returned artifacts, versions, scope and review evidence; use an authorized reviewer with real playback/inspection when required. Mark unverified content honestly. Send defects to their earliest owner, recheck affected dependencies and continue until the endpoint or a concrete blocker/stop limit.
7. Deliver the requested artifact first, then actual validation state, residual issues and next decision if blocked. A finished-film request requires the actual assembled media; task packages, prompts and QC reports cannot substitute.

## Role map

These are responsibilities, not claims that an implementation is installed. The host resolves each code to an available capability; one installed role may cover several tasks. Do not require sibling package paths or private runtime files. Keep specialist craft in its owning role, not a duplicate rulebook here.

| Code | Owns |
|---|---|
| DIRECTOR | creative concept, story/season, character action, dialogue, performance, director decisions before storyboarding |
| STORYBOARD | viewing order, blocking, cinematography, shot continuity |
| CHARACTER_ASSET | character identity, appearance, wardrobe and state references |
| SCENE_ASSET | location layout, entrances, landmarks, light sources and materials |
| PROP_ASSET | prop form, structure, material, handling and state |
| GENRE_VISUAL | genre-specific visual language applied to existing story, assets and shots |
| PRODUCTION_CONTROL | task-specific brief and acceptance, source/asset inventory, continuity, versions, budget/rights/change records |
| VIDEO_PRODUCTION | actual generation, selection, editing, sound, playback review and repair |
| MARKET_RESEARCH | market questions answered from verifiable official sources |
| KNOWLEDGE_REVIEW | review and versioned writing of approved knowledge |
| WEB_INTERFACE | website or application interface design and implementation |

Refine the owning role's task rather than inventing an unavailable specialist:

| Symptom | Owning task |
|---|---|
| Repetitive episodes, weak season payoff, interchangeable people or unmotivated performance | DIRECTOR: season/relationship/reveal development, playable objectives, listening and cross-scene performance |
| History resets, future threads close early, changed episodes do not update downstream | PRODUCTION_CONTROL: history replay, timeline context, versioned change scope and rechecks |
| Uneditable coverage, weak take selection, picture-lock or reconform mismatch | STORYBOARD for planned coverage; VIDEO_PRODUCTION for edit development, locked-cut turnovers and actual playback |
| Color, repair, dialogue, ambience, mix, subtitle or master mismatch | VIDEO_PRODUCTION: separate image, sound and delivery tasks using the actual target requirements |
| Budget, rights, upload permission or change approval unknown | PRODUCTION_CONTROL records the gap; VIDEO_PRODUCTION stops the affected execution until the proper authority resolves it |
| Automated checks passed but no complete film/multi-episode evidence | VIDEO_PRODUCTION: evidence-scoped real-media validation; maintenance alone never authorizes generation |

## Problem triage rules

1. Restate the observable symptom with source, location, current version and evidence; text or a thumbnail is not proof of an unseen clip.
2. Find the earliest responsible layer: source, screenplay, directing, storyboard, assets, previs, keyframes, prompts, generation, sound, editing, state or delivery. The noticing role need not own the repair.
3. Split independent defects and order tasks from the earliest layer outward. Downstream work waits for corrected, rechecked inputs; never route "regenerate" as a fix for a defect whose cause has not been located.
4. Each task states scope, locks, inputs, output, review criteria, dependencies and forbidden changes. A role returns evidence for its scope, not approval of unrelated layers.
5. Recheck the diagnosis after every handoff. Stop for material permission, spend or locked-meaning conflicts; do not restart unaffected work.

### Triage output

For diagnosis-only requests return:
1. **Symptom and evidence** — what is wrong and how it was observed.
2. **Earliest responsible layer** — and why later layers cannot fix it alone.
3. **Routing table** — role code, task, inputs, expected output, recheck criteria, order.
4. **Blocked or unknown items** — what must be decided or verified before work proceeds.
5. **Not routed** — problems deliberately left out of scope and why.

For an authorized repair request, continue the loop rather than treating this table as completion.

## Boundaries

- The orchestrator coordinates available specialist execution; it does not replace their craft, bundle models/accounts/credits, grant approval, or automatically obtain an independent reviewer.
- It does not guarantee that the host can switch skills automatically. No delegation means an explicit blocked handoff, not simulated tool calls or a claim of completion.
- Diagnosis remains a hypothesis until actual material is checked. Review records require real scope, evidence, reviewer and authority; neither a hash nor "delegated" self-label proves independent approval.
- User-locked story structure, shot order, timing and dialogue are preserved unless the user authorizes a change.
- Missing media, permissions, budget or inspection capability stops only the affected work. Preserve the last verified version and disclose the exact unfinished scope.
