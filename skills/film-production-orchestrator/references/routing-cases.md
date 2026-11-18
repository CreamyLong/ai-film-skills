# Routing cases

Worked examples of symptom-to-role assignment. Each case names the observable symptom, the earliest layer that can own it, and what must be rechecked before downstream work resumes. These are routing hypotheses, not media diagnoses.

## Story and directing

| Symptom | Earliest layer | Route | Recheck |
|---|---|---|---|
| Plot does not connect between scenes | Screenplay | DIRECTOR | Cause and effect chain, character knowledge and goals |
| Character acts against established motive | Screenplay | DIRECTOR | Behavior, alternatives rejected, consequence |
| Dialogue says one thing, scene needs another | Screenplay | DIRECTOR | Subtext, listener effect, character voice |
| Audience cannot tell who controls the scene | Directing | DIRECTOR, then STORYBOARD | Power geometry, viewing order |
| 每句台词切一次近景，连起来像台词轮播 | Storyboard | STORYBOARD：可看性诊断 | 按攻守单元并镜、只在权力/知情变化处切 |
| 重话抛出后没有接招反应 | Directing or storyboard | DIRECTOR, then STORYBOARD | 听者完成一个可观察的策略/关系变化 |
| 镜头时长均匀、没有重音，或全片同尺寸近景 | Storyboard | STORYBOARD：可看性诊断 | 主力景别、Hero Frames、重音换档有理由 |
| TTS 每句都像读稿，重音和气口不承担戏 | Sound performance | SOUND_ASSET, then VIDEO_PRODUCTION | 逐句 pace/energy/emphasis/pause/delivery 字段与实际听感 |

## Assets

| Symptom | Earliest layer | Route | Recheck |
|---|---|---|---|
| Same character looks like a different person across shots | Character asset or keyframe | CHARACTER_ASSET, then VIDEO_PRODUCTION | Reference identity against actual keyframes |
| Room layout changes when the camera reverses | Scene asset | SCENE_ASSET, then STORYBOARD | Shared layout, entrances, landmarks, light direction |
| Prop changes hands or state without explanation | Prop asset or storyboard | PROP_ASSET or STORYBOARD | Prop lifecycle and shot-to-shot handoff |
| Character or prop appears with no prepared asset | Asset inventory | CHARACTER_ASSET, SCENE_ASSET or PROP_ASSET | Every visible subject has an approved reference |

## Keyframes and prompts

| Symptom | Earliest layer | Route | Recheck |
|---|---|---|---|
| Keyframe already shows the wrong subject or framing | Keyframe | VIDEO_PRODUCTION keyframe review, with asset roles as needed | Actual image against storyboard and assets |
| Prompt asks for a hand close-up but adds facial performance | Prompt compilation | VIDEO_PRODUCTION | Compiled text against visible subjects and body regions |
| Dialogue exists in the script but not in the submitted prompt | Prompt compilation | VIDEO_PRODUCTION | Source dialogue against the actual submission record |
| Reference images exceed model capacity | Submission | VIDEO_PRODUCTION | Declared attachments against the actual request |

## Generation and sound

| Symptom | Earliest layer | Route | Recheck |
|---|---|---|---|
| Voice changes between clips of the same character | Sound asset or sound route | SOUND_ASSET, then VIDEO_PRODUCTION | One reviewed voice source per speaker and alias mapping; voice reference actually attached, then actual audio |
| Speaking character has no prepared or approved voice | Asset inventory | SOUND_ASSET | Every speaker has one listened-to voice source with recorded rights |
| Two characters cannot be told apart by ear | Sound asset | SOUND_ASSET | Blind comparison on the same neutral line |
| Background changes between angles of one room | Scene asset or generation | SCENE_ASSET, then VIDEO_PRODUCTION | Spatial ledger against actual frames |
| Previous clip tail does not match the next opening | Editing or generation | VIDEO_PRODUCTION | Actual tail and head frames, not redrawn stills |
| Generated clip is a still slideshow | Generation | VIDEO_PRODUCTION | Real motion in the actual clip |
| Old clip reused after prompt or reference changed | Ledger or state | VIDEO_PRODUCTION | Current request fingerprint against the stored one |

## Whole film

| Symptom | Earliest layer | Route | Recheck |
|---|---|---|---|
| Individual clips pass but the film does not read as one story | Screenplay or editing | DIRECTOR, then VIDEO_PRODUCTION | Full playback at normal speed |
| Novel adaptation loses the causal spine | Source breakdown | DIRECTOR | Source spans against screenplay decisions |
| Scenes are missing or assembled out of order | Ledger or editing | VIDEO_PRODUCTION | Scene order and completeness against the plan |
| Market or genre question blocks a creative decision | Research | MARKET_RESEARCH, then DIRECTOR | Dated official sources, stated limits |

## Routing topology

- 路由是**有向无环图**：用户意图 → 总控/路由入口 → 最早责任角色 → 复核证据 → 下游。执行依赖不得成环；A 把任务交给 B 后，B 不能把同一决定再交回 A 形成回环。
- 交叉引用可以双向，用于阅读导航；但“文档互链”不等于“技能会被自动加载”。命中首先取决于 frontmatter 的 `description` 触发词、明确职责和不适用边界。
- 一个症状只设一个最早责任角色；后续角色是复核/执行，不是共同所有权。需要回退时回到最早责任层，不新开环。
- 不用新增“万能 Skill”解决命中问题；优先把触发词、反例和路由行补进现有职责包。

## Not routing

- A request that already names its stage and artifact (for example "rewrite this dialogue") goes straight to the owning role without full-project planning; continue through the host when available and requested.
- A routing decision never replaces the owning role's own review of the actual material.
- If two layers could own a symptom, route to the earlier one first and state what evidence would move it downstream.
