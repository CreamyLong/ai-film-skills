# MiniMax H3 时间线导演台（TimelineDirector）运行时适配

目标运行时是 ComfyUI + `ComfyUI-MiniMaxH3-TimelineDirector` 插件时读本文件。它是 H3 Ref2VA 路线下的**运行时适配层**：提示词仍按 [context-ir-format.md](context-ir-format.md) 的六段结构写，本文件说明怎样把素材、分段、音频与参数交给这个插件，并把它的全部能力用足。

本文行为按插件 commit `050226d`（2026-10）源码核实；插件升级后先重跑 `scripts/timeline_plan_check.py` 的回归并复核第 7、8、13 节，未核实的新行为按 [provider-shells.md](provider-shells.md) 记为 `unverified`。插件为 GPL-3.0，本文只描述行为，不复制其文档或代码。

## 0. 强制触发条件（不要只用单段 H3）

只要出现以下任一条件，本文件就是必读运行时适配，不能把整个任务编译成一条 H3 base prompt，也不能只生成一个单段就交付：

| 条件 | 应触发的能力 |
|---|---|
| 目标时长超过单次 H3 生成（官方 4–15 秒） | 多段拆分 + 合并 |
| 同一条连续动作被时长拆成多段 | `segmentConfig` 多段 + 正重叠续写；切镜仍写在段内 `[Shot N]` |
| 同一条连续动作内含多个 `[Shot N]` 切点，或整集需要跨段镜头号映射 | 全局镜头号与段内 `[Shot N]` 映射；切点必须仍在同一条连续动作内 |
| 单段 5–15 秒但需要多图锁身份、参考音频或统一规划 | 单段 `segmentConfig`（`count = 1`）或 H3 base，按素材复杂度选 |
| 需要同时锁两个以上人物身份 | 每段分配实际需要的 `<Picture N>`，不把全剧素材塞进每段 |
| 使用参考音频、保留原生音频或 locked audio | 明确 `audioMode` 与音频路由；locked 必须每段同文件同 `trimStart` |
| 需要段级重抽、接缝修复或重叠续写 | 原生 Loop 节点组逐段观察，或合法的段间重叠；不用 RGB 拼接冒充连续镜头 |
| 没有对白但长视频模型可能自行发声 | 在 `overall_soundscape` 明确只有环境声/脚步/风，不出现人声 |

**只有**单镜 4–15 秒、单张参考图、无参考音频且不需要长视频拆分时，才可留在 H3 base 模式。
### 0.1 场级多镜配方（官方能力）

官方 H3 prompt 支持在同一次 5–15 秒生成里用 `[Shot N] At …` 切镜；时间线插件也允许每段 prompt 内含切点。生产上按场组织：

| 场的总时长 | 生成方式 | 切点写在哪 |
|---|---|---|
| ≤15 秒 | **一场一次执行**，`segmentConfig.count = 1` | 同一段 prompt 内，`[Shot 2] At 00:0X.XXX, the shot cuts to …` |
| >15 秒 | 按**同一条连续动作**拆 2–3 段，段间正重叠 22 帧 | 切点仍写在段内；段边界不要放在切镜上 |
| 需要换场/时间跳跃 | 另起一场/一段 | 不靠 0 重叠把无关镜头串起来 |

示例（一场 10 秒、两个镜头）：

```text
[Shot 1] ... 门口过肩，门打开，沈远停在门槛 ...
[Shot 2] At 00:07.290, the shot cuts to a tight close-up on <Subject 2> (S2) ...
```

来源：`MiniMax-AI/MiniMax-H3` 仓库的 h3-prompt-writing 的 base 参考文档第 86–92 行（`[Shot N]` 与 `the shot cuts to`），以及插件 `Songssx/ComfyUI-MiniMaxH3-TimelineDirector` README 的 per-segment prompt 说明。


段内 `[Shot N]` 可表达已核实的机位和景别切换。跨生成窗的正重叠只续接同一条连续动作；独立场景和时间跳跃另行生成再剪。

**官方的多镜能力写在“段内 prompt”，不是靠段边界拼。** H3 支持单次 5–15 秒内多个 `[Shot N]` 切镜；超过 15 秒时按同一条连续动作拆段，切镜仍写在段内。不要用 0 重叠把互不相关的镜头串成长链——0 重叠不复制 latent，表演、光位、方向和底噪都不会继承，等同于“同一次执行里各跑各的”。

切点动机、连续性锚点和 AI 素材接缝的技术处理见 [transition-causality.md](transition-causality.md)。

### 最小激活清单

1. 建立全局镜头计划：`global_shot_id`、`segment_id`、`target_duration`、`overlap_duration`、`new_shots`、`visual_refs`、`audio_refs`。
2. 使用 `MiniMaxH3TimelinePlanner` → `MiniMaxH3FiniteSegmentSampler`；不要用兼容版单节点“时间线导演台”代替多段主路径。
3. 每段长度落在 `5 + 17n` 帧；段间无空洞；连续动作使用正重叠（5、22 或 39 帧），**生产默认不用 0 重叠**。
4. 每段有自己的 `images[]`、`audios[]`、完整提示词；标签在每段从 `<Picture 1>` 重新编号，不能拿全剧图片数量当段内编号。
5. 有对白时先过 `dialogue_preflight.py`；长视频的每段台词都要逐段检查，不能只检查总稿。
6. 提交前对实际 `timeline_data` 运行 `scripts/timeline_plan_check.py`；`block` 必须修，`review` 要写证据。
7. 生成后核对成片时长是否等于 `目标输出帧数 / 24`，并检查段间接缝、身份、服装、道具、光源、轴线、声音和口型。
8. 段级失败先回到该段；一键采样器和低内存版都不能只重跑单段，需要逐段观察时改用原生 Loop 节点组，否则重跑整组并保留上次检查结果，不把失败片段继续传给下游。

### 低显存与 Pika 兼容

- 16G 级显存先用较低草稿分辨率（例如 640×352）跑通分段逻辑，确认后再做正式分辨率；二采先关闭。
- 4 步加速 LoRA 必须与 UNet 同模型家族：Pika LoRA 与 Pika UNet 配对，MiniMax turbo LoRA 与对应 MiniMax base/ref2va 配对；不要混用两套蒸馏。
- 本插件用 `<Picture N>/<Video N>/<Audio N>` 稳定编号；不要使用其他 fork 的 `@CHR`/`@SCN` 标签，除非目标运行时明确支持并已实测。
- 无对白段在声音字段写清只有脚步、风、衣料、环境声，不写“无字幕/无人声”式负面清单来赌模型行为。

## 0.2 必须先看的官方材料与误用清单

运行时行为以插件源码/README 为准；升级后重新核对以下链接，不凭记忆写参数：

- 插件仓库：[Songssx/ComfyUI-MiniMaxH3-TimelineDirector](https://github.com/Songssx/ComfyUI-MiniMaxH3-TimelineDirector)
- 中文说明：[README_CN.md](https://github.com/Songssx/ComfyUI-MiniMaxH3-TimelineDirector/blob/main/README_CN.md)
- 长视频 Agent 指南：[AGENT_LONG_VIDEO_GUIDE_CN.md](https://github.com/Songssx/ComfyUI-MiniMaxH3-TimelineDirector/blob/main/docs/AGENT_LONG_VIDEO_GUIDE_CN.md)
- 官方 H3 提示词规范：[MiniMax-AI/MiniMax-H3](https://github.com/MiniMax-AI/MiniMax-H3)
- 官方权重与 4/8 步 turbo LoRA：[Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3)

### 常见误用

| 误用 | 后果 | 正确做法 |
|---|---|---|
| 31 秒塞进 `count = 1` 的单段 | 753 帧从第一帧起是噪声 | 拆 3 段（277/277/243），22 帧重叠 |
| 单段超过 362 帧 | 超出 H3 训练区间，整段 latent 失效 | 每段 ≤362 帧，按连续动作拆分 |
| 把 Material Plan 接有限分段采样 | 报 `Disconnect Prompt Index…` 或只生成一段 | 接 **Segment Plan**（第三个输出） |
| 接 Segment Plan 时仍连 `prompt_index` | 素材被段索引过滤 | 生成全部段时断开 `prompt_index` |
| 用 0 重叠把换机位镜头串成长链 | 不继承 latent，等于各跑各的 | 切镜写段内 `[Shot N]`；跨段只用于连续动作 |
| 后段 prompt 不写重叠区 | 接缝处人物/光位跳变 | `[Shot 1]` 先复述重叠区，再写新内容 |
| 每段音频文件/trimStart 不一致却用 locked | 最终音轨错位 | locked 必须每段同文件、同 trimStart |
| 用 `@CHR`/`@SCN` 等其他 fork 标签 | 标签不被识别 | 只用 `<Picture N>/<Video N>/<Audio N>` |

提交前必须对实际 `timeline_data` 跑 `scripts/timeline_plan_check.py`；段长、重叠、`count`、标签任何一项不合法都不提交。

## 1. 它解决什么、什么时候用

H3 单次推理只能出 4–15 秒（官方训练区间约 124–362 帧），参考素材每次最多 9 图、3 段视频、3 段音频、合计 12 个。插件在语法上允许单段最长 3592 帧（约 150 秒），但超过 362 帧已超出训练区间，质量未经证实；长镜头仍应按连续动作拆成多段，不要拿“插件能跑”当作“模型能拍好”。插件解决五件事：

1. **一次执行出长视频**：按时间框把目标时长拆成多段，在一次 ComfyUI 执行内逐段采样；后段直接从前段的 AV latent 尾部续写（不经 RGB 解码再编码），全段共用一个种子，接缝处有 Drift-Control 视频遮罩与 Soft AV 音频渐放，最后自动去掉重叠并合成音画。
2. **参考素材编排**：视频、图片、音频放在同一条时间线上，可移动、裁剪、切分；每段视频可选三种用途（第 6 节），每段可分配不同的图片和音频。
3. **稳定的标签编号**：`<Picture N>/<Video N>/<Audio N>` 的顺序与编码器一致，可由计划离线算出（第 8 节）。
4. **原音锁定**：上传的音频或参考视频原声可锁定为最终音轨，口型仍受其驱动——数字人、唱歌、配好的对白都靠它（第 7 节）。
5. **SelfLift 二采**：低清采样大部分步数，经 H3 Latent Upscaler 放大后再用少量高清步补细节（第 10 节）。

选用判断：

| 需求 | 用法 |
|---|---|
| 单镜 ≤15 秒、只靠首帧/首尾帧 | 不必用本插件，走 H3 基础模式（[h3-base-format.md](h3-base-format.md)） |
| 多参考图锁身份、需要参考视频/音频、需要按时间放置素材 | 本插件单段 |
| 单镜 >15 秒的连续镜头、长时长数字人、同一条连续动作被拆成多个 GEN 窗口 | 本插件有限分段 |

## 2. 节点与工作流怎么选

| 节点/工作流 | 什么时候用 |
|---|---|
| **素材规划台 → 有限分段采样**（默认） | 一切新工作。规划台的 **Segment Plan（第三个输出）** 接采样器的「有限分段规划」；单段、多段、文生、参考生都用同一张图 |
| **有限分段采样（低内存版本）** | 长时长或高分辨率：每段解码后立即编码为临时视频并释放帧内存，直接输出 `VIDEO` 给保存节点；支持二采，但不保存 latent checkpoint（只保留末段 latent 输出），也没有片段重跑 |
| **原生 Loop 节点组** | 需要逐段预览、保存或在每段之间插入自定义处理时使用。连线：`初始化分段循环 → Start Loop → 选择循环分段 → 规划编码器 → 准备循环分段 → 采样/二采 → VAE 解码 → 合并循环分段 → End Loop → 完成分段循环`。仍没有磁盘片段缓存和选择性单段重跑，但能把失败停在当前段下游之前 |
| **规划编码器（公开节点）** | 在原生 Loop 循环体里对当前段做 H3 编码；一键采样器内部也复用它，不需要手工展开 |
| **Omni 素材包提示词桥** | 让多模态提示词重写器先读完有序素材再写 H3 提示词；需另装 Prompt Rewriter Omni。重写结果仍要按本 Skill 预检，不能直接视为合格提示词 |
| **时间线导演台（兼容）** | 旧的一体化单段节点：自带 `prompt` 输入，只渲染一个时间窗，不支持分段与原音锁定 |
| **导出预设 / 本地预设加载器** | 保存与复用素材编排（第 11 节） |

规划台有三个输出，接错会直接失败或只生成一段：

- **Material Plan（第一个输出）**：只输出 `activeIndex` 高亮的这一段的素材，并带 `prompt_index`。它是给单段生成、逐段材料过滤或提示词重写器用的。
- **Omni Media Bundle（第二个输出）**：给 Omni 提示词桥的素材包。
- **Segment Plan（第三个输出）**：完整多段计划，有限分段采样必须接这个。把 Material Plan 接进有限分段采样时，插件会报 `Disconnect Prompt Index when generating all timeline segments`，因为该输出已经被段索引过滤。

`Prompt Index` 是规划台的 1-based 段索引输入，用来按段过滤 Material Plan 的素材；接 Segment Plan 生成全部段时必须保持断开。

## 3. 任务配方

每行是一种用法的完整设置；第 5 节解释字段。所有视频片段都要显式写 `referenceMode` 与 `hasAudio`，有视频时显式写 `videoAudioEnabled`。

| 任务 | 素材 | 视频用途 | 音频设置 | 提示词要点 |
|---|---|---|---|---|
| 文生视频 / 文生长视频 | 无 | — | H3 生成 | 单段写 `globalPrompt`；多段用时间框，可全局复用或逐段写 |
| 参考图生视频（锁身份/场景） | 图片：关键帧在前，人物、场景参考在后 | — | H3 生成；可加独立音频作音色参考 | 每张图在 `subject_definitions` 说明职责 |
| 音色一致的对白 | 图片 + 角色音色样本（`audioMode: "reference"`） | — | H3 生成，`<Audio N>` 只参考音色 | `retention_analysis` 用 `reference`，不复制样本里的台词 |
| 数字人 / 已配好的对白 / 唱歌 | 人物图 + 成品音轨（`audioMode: "locked"`） | — | 锁定音轨：每段都分配同一文件、同一 `trimStart` | 锁定音轨没有 `<Audio N>` 标签；按音轨实际内容写 `<d>` 台词与口型 |
| 换人、换装、换风格 | 原视频 + 新人物图 | `edit` | 留原声：`hasAudio: true`；要新声音：`hasAudio: false` | 原视频是 `<Video N>`，新人物用 `<Picture N>` 定义 |
| 动作迁移 | 动作源视频 + 目标人物图 | `edit` | 同上 | `retention_analysis` 写清只取动作、不取人物外观 |
| 只锁首尾构图 | 参考视频 | `boundary` | 按需 | 中段运动由提示词决定 |
| 同一镜头的长链续写 | 可无新素材 | — | H3 生成（Soft AV 续接） | 时间框正重叠（第 9 节）；后段 `[Shot 1]` 先复述重叠区 |
| 同一条连续长镜被时长拆段 | 每段各自的图片/音频 | — | H3 生成 | 正重叠续写；后段 `[Shot 1]` 先复述重叠区 |
| 单次 5–15 秒内的多镜切换（换机位/景别） | 各镜素材按段内标签准备 | — | 同一段内 H3 生成 | 用 `[Shot N] At …` 写在同一条 prompt；切点按 [transition-causality.md](transition-causality.md) 设计 |
| 接上一次已生成的成片 | 上一段成片作视频片段，盖住生成区开头 | `guide` | 要新声音必须 `hasAudio: false` | `[Shot 1]` 先描述固定 Guide 中的画面 |

## 4. 素材导入

- 所有素材必须位于 ComfyUI 的 input 目录之下，计划里写相对路径；目录外的路径会被拒绝。界面上传的文件落在插件自己的子目录里，API 提交时同样写相对 input 目录的路径。
- 全局素材库不限数量；每段实际可用最多 9 张图、3 段视频窗口、3 段参考音频，合计不超过 12（含视频原声）。
- 图片解码时按画布 `width × height` 适配；每段视频可单独设 `referenceWidth/referenceHeight`（对齐到 32），降低参考 latent 计算量而不改变成片画布。
- 分段时图片和音频按 **id** 分配给各段，不按列表位置；删除或重排全局素材库不会让某段悄悄换文件，但写错的 id 会被静默丢弃。

## 5. `timeline_data` 字段

| 位置 | 字段 | 含义 |
|---|---|---|
| 节点 | `generation_seconds` | 生成时长（秒），与青色 GEN 选区双向同步。分段时它是总时长，单段时是唯一片段长度；最大 150，但超过 15 秒超出训练区间 |
| 节点 | `prompt_index` | 1-based 段索引；连接后 `Material Plan` 只输出该段素材。接 `Segment Plan` 生成全部段时必须断开 |
| 顶层 | `selection.start/duration` | 生成区（秒）。未分段时就是本次生成窗口；分段时各段用 `startFrame/endFrame` 覆盖它 |
| 顶层 | `length` | 规划器把 `generation_seconds` 对齐到 `5 + 17n` 后的帧数；单段模式直接用它 |
| 顶层 | `images[]` | `{id, file, name}`；顺序即未分段时的 `<Picture N>` 顺序 |
| 顶层 | `audios[]` | `{id, file, name, audioMode, trimStart, duration}`；`audioMode` 为 `reference` 或 `locked` |
| 顶层 | `videoClips[]` | `{id, file, name, start, duration, trimStart, hasAudio, referenceMode, referenceWidth, referenceHeight}`；`start` 是时间线位置，`trimStart` 是源文件入点 |
| 顶层 | `videoAudioEnabled` | 参考视频原声总开关；决定锁定、静音还是生成（第 7 节） |
| 顶层 | `globalPrompt` | 全局提示词：未分段时使用；分段且没有任何段落提示词时复用于每段 |
| 顶层 | `secondPass / secondPassModel / secondPassHighSteps` | 二采开关、Latent Upscaler 文件名、高清步数 |
| 顶层 | `segmentConfig` | `{count, mode: "timeline", activeIndex, segments[]}`；`count` 为 0 时走单段模式 |
| 每段 | `startFrame / endFrame` | 整数帧（24 fps），时间线全局坐标；段长必须 `5 + 17n` |
| 每段 | `images[] / audios[]` | 该段使用的素材 id，顺序即该段内的标签顺序 |
| 每段 | `prompt` | 该段完整的六段式提示词；主规划路径不会自动注入续写说明 |

`count = 0` 时规划器把当前 GEN 选区当成唯一段：必须写 `globalPrompt`，长度对齐到 `5 + 17n` 且不超过 3592 帧。这是文生/参考生的单段路径，不是“多段退化成一段”。

`segmentConfig.activeIndex` 只影响 `Material Plan` 输出（选中哪一段的素材），不影响 `Segment Plan`；一键采样器读的是完整 `Segment Plan`，所以不要指望改 `activeIndex` 能只重跑一段。

采样器侧的 `seed` 对所有段共用；`continue_audio_latent`（默认开）控制段间音频是否走 Soft AV 续接；`ref_image_size` 见第 10 节。

## 6. 三种视频用途

| `referenceMode` | 行为 | 适用 |
|---|---|---|
| `guide`（固定 Guide） | 与生成区重叠的帧按时间位置逐帧锁定 | 续写、保持运动与站位 |
| `edit`（可编辑参考） | 只作参考，不锁原人物 | 换人、换装、换风格、动作迁移 |
| `boundary`（仅固定边界） | 只锁重叠区的首帧和末帧 | 只要首尾构图一致 |

三种用途在本版本中都会占用 `<Video N>` 编号（与生成区相交的部分，超过 15 秒拆成多个窗口，各占一个编号）。不要把需要替换的人物区域设为 `guide`。

## 7. 音频路由（最容易出错）

有限分段采样的最终音轨只有三种来源，按以下顺序判定：

1. **锁定上传音轨**：任一段有 `audioMode: "locked"` 的音频 → 必须每段都分配、且文件与 `trimStart` 相同；最终音轨是原波形，H3 不生成声音，口型受其驱动。
2. **锁定视频原声**：有参考视频、其 `hasAudio` 不为 false、且 `videoAudioEnabled` 不为 false → 最终音轨是时间线上的视频原声（没有视频覆盖的时段为静音），H3 不生成声音。
3. **静音**：有参考视频且所有段 `videoAudioEnabled: false` → 最终输出静音；关掉原声**不会**让 H3 补生成声音。

以上都不成立时才由 H3 生成声音。因此：**要用参考视频、同时要 H3 生成新对白或音效，把该视频片段设为 `hasAudio: false`，`videoAudioEnabled` 保持 true**。兼容导演台不做锁定，视频原声只作为配对的参考音频编号。

`audioMode: "reference"` 与 `"locked"` 是两种不同注入方式，不要混用概念：

- `reference` 把 WAV 编码成参考音频条件（`<Audio N>`），H3 仍生成新声音；音色受参考影响，但台词可能被模型改写或遗漏。
- `locked` 把 WAV 编码后直接替换目标 AV latent 的音频流，音频 `noise_mask` 全为 0，音频分支不再去噪；视频分支继续生成并 attend 到这条固定音轨，最终音轨用原始 WAV 整轨替换。locked 不会修正 TTS 读错的词，只会原样保留。

因此固定台词的正脸镜适合 locked，但必须先做 TTS 内容回读；reference 适合让 H3 自己表演，但仍要听辨台词是否说对、说全。单镜实测见 [audio-route-ab.md](audio-route-ab.md)。

## 8. 标签编号规则

- `<Picture N>`：该段图片按顺序从 1 编号（未分段时用全局顺序）。
- `<Video N>`：与该段生成区相交的视频窗口，按时间线从左到右编号。
- `<Audio N>`：先编该段的独立参考音频（锁定音轨不编号），再接各视频窗口的配对原声（仅当原声启用）。
- 分段后每段都从 1 重新编号；全局计划用全片镜头号，提示词内用段内编号，两者映射要记录。
- 规划台输出的 Omni 素材包里带有与编码器一致的标签清单；提交前用 `scripts/timeline_plan_check.py` 离线得到同样的逐段清单并核对提示词。

## 9. 分段、重叠与段提示词

重叠不是一个“拼接参数”，而是插件把上一段 AV latent 的尾部交给下一段继续采样的核心机制。它只服务**同一条连续动作**被时长拆段的情况；独立镜头不要用它拼在一起。按采样层的 `overlap_frames` 分三支：

| 重叠 | 采样层行为 | 适用 |
|---|---|---|
| `0` | 两段完全独立：不复制上一段 latent、不装 Guide、合并时不删帧 | 语法允许；但 0 重叠没有连续性收益，只适合确实无需继承的段，不能靠它把无关镜头串成长链 |
| `1` | 贴边：把上一段最后一帧经 `_apply_h3_guides` 钉成下一段第 0 帧 Guide，只锁边界构图 | 只要求接缝构图一致，不要求运动连续 |
| `>1` | 标准续写：上一段 latent 尾部复制到下一段开头，重叠区噪声遮罩为 0（完全保留），重叠之后为 1（全新去噪）；同时启用 Drift-Control 与音频 Soft AV | 同一条连续动作/运镜/对白的跨段续写 |

### 9.1 提示词层：重叠区永远属于上一段

- **主规划路径不会自动注入续写说明。** 只有已弃用的 `MiniMaxH3FiniteSegmentExpansion` 节点有 `inject_continuity_instruction`（默认开）；`MiniMaxH3TimelinePlanner → MiniMaxH3FiniteSegmentSampler` 这条主路径没有这个开关。第 2 段及以后，作者必须在 `[Shot 1]` 里自己写：开头 `00:00.000–00:0X.XXX` 是上一段的 latent 续接，必须保持人物位置、环境、运动、运镜、光线、色彩与声音，再引入新动作。没有 `[Shot 1]` 的续写段会被 `timeline_plan_check.py` 报 `CONTINUATION_SHOT1_MISSING`；写了但没复述重叠区，只会得到 `CONTINUATION_SHOT1_REVIEW`，需要人工确认。
- 续写段的 `[Shot 1]` 先准确复述重叠区里已经存在的画面，不能为了把新内容写成 `[Shot 1]` 而忽略或错误描述固定 Guide。
- 重叠结束后如果仍是同一镜头，写 “After 00:0X.XXX, the same uninterrupted shot continues as …”，不要人为制造剪辑点。
- 重叠结束处如果本来就该切镜，新镜头从实际切点写成 `[Shot 2] At 00:0X.XXX, the shot cuts to …`；不要假装它从第 0 帧开始。
- 单段生产（`segmentConfig.count = 0` 或 `1`）没有上一段，不需要这段说明；只有真正使用正重叠续写时才按本节写。

### 9.2 采样层：latent 续接、Drift-Control 与音频

- 所有段共用采样器上的同一个 `seed`；后段不是重新起一张图，而是从上一段 `sampled` 的 AV latent 尾部继续。每段的 `RandomNoise` 都用同一个种子。
- **重叠值不是单独填的参数**，而是从两个 GEN 窗口算出来的 `previous_end - start`。写 `startFrame/endFrame` 时让相邻窗口实际相交，相交帧数就是重叠；时间框路径要求它正好是 0、1 或 `5 + 17n`，否则直接报错；旧的有限扩展节点才会向下取整。
- `overlap > 1` 时，插件先把重叠帧向下对齐到 H3 合法网格（例如 24→22、48→39），复制上一段 latent 尾部到本段开头，用线性时间遮罩把重叠区固定为保留、之后为全新去噪；同时按遮罩的视频 token 数安装 Drift-Control，只对临时视频前缀动态加噪，接缝侧保持干净。
- 音频默认走 Soft AV：重叠音频前部完全保护，最后 8 个音频 latent tick 用半余弦释放到新生成声音；锁定音轨或静音时改走零去噪的 locked/silent 音轨路径，最终整轨替换。此时 `continue_audio_latent` 不会让 H3 续写声音，输出音轨按锁定/静音路径整轨替换。音频 latent 约 40 tick/秒：22 帧重叠对应约 37 个 tick，只有末尾 8 tick（约 0.2 秒）做渐变，其余重叠区完整保留旧声音；合并时裁掉前段尾部重叠采样，接上后段完整音频，渐变因此留在成片里。它解决的是接缝爆音、相位/音量跳变和重复声音，**不解决台词没说出来、人物音色不统一或镜头内容错误**——这些仍要靠逐段提示词、统一 `audio_refs`、足够时长和重跑。
- `overlap = 1` 的贴边分支只钉上一段最后一帧，不做 latent 尾部复制；`overlap = 0` 分支直接返回，不做任何续接。`overlap = 1` 需要上一段解码图、VAE 与音频 VAE；`overlap > 1` 需要上一段 sampled latent，缺一个都会报错。
- 开二采时，SelfLift 会把上一段原生低清 latent 的 `selflift_low_resolution_carry` 一并带进下一段，避免 Drift-Control 重新缩小高清 latent 造成边界模糊或闪白；这是二采长视频接缝比逐段放大更稳的原因。

### 9.3 合并：前段拥有重叠区

- 合并时第一段完整保留；第 2 段及以后由 `MiniMaxH3FiniteSegmentFinalize` 裁掉开头的 `trim_frames`（等于实际重叠帧数），保留前段解码出的尾部。这样切点处不会重复帧，也不会把重叠区算两次。
- Soft AV 模式下，音频先由 `MiniMaxH3FiniteAudioTrimTail` 裁掉前段尾部重叠，再由 `AudioConcat` 拼接，后段的半余弦释放区保留在最终音轨里；非 Soft 模式则与视频同步裁掉重叠头部。
- 成片总帧数等于最后一段的终点帧；每段实际贡献的新帧 = 段长 − 重叠。规划器给出 `target_output_frames` 时，最后由 `MiniMaxH3FiniteOutputTrim` 把自动补出的尾巴裁回目标帧数，音轨同时按帧数裁样。
- 采样器的 `Last Sampled Latent` 只是**最后一段**的完整 AV latent，不是整条成片的合并 latent；不要把它当作“整条长视频 latent”再喂给下一次执行。要续写就继续加段，不要拿末段 latent 冒充全片上下文。
- 合并帧默认留在内存；长片或高分辨率可用低内存版本，或设置 `H3_MERGED_FP16=1` 让合并帧以 float16 保存（减半内存，实测无可感知差异）。

### 9.4 参数与选择

- 每段长度必须是 `5 + 17n` 帧，最大 3592 帧（约 150 秒），但 H3 训练区间约 124–362 帧（5–15 秒）；超过 362 帧插件仍会跑，质量未验证。段数 1–64；第一段从第 0 帧开始；后段起点和终点都要前进，段间不能有空隙；重叠必须大于等于 0 且小于相邻两段的较短长度。**turbo 4-step LoRA 必须配 `simple` scheduler。** 2026-11 实测：同一镜把 scheduler 改成 `normal` 或 `beta`，输出整幅过曝、条纹和换脸崩坏；官方“beta/normal 更适合参考重场景”的建议针对非 turbo 的基础模型，不适用于 4-step 蒸馏 LoRA。**单段不要超过 362 帧**：2026-11 实测 753 帧单段从第一帧起就是噪声，不是后段漂移，而是超出训练时长后整条 latent 失效。
- 重叠必须是 0、1 或 `5 + 17n`（5、22、39、56…）；时间框路径直接拒绝非法值，旧的有限扩展节点会向下取整。实际重叠取相邻窗口的相交帧数，不取提示词里写的时长。
- 静态镜头取 5 或 22 帧；动作、运镜或跨段对白取 22–39 帧（约 0.9–1.6 秒），覆盖动作趋势与语气。不要把接缝放在嘴型中间、快速闪切或最模糊的一帧。
- 只要求首尾构图一致、参考视频中段可自由变化时，用视频片段的 `referenceMode: "boundary"`：只解码重叠区首帧和末帧作 `boundary-start`/`boundary-end` 两个单帧 Guide，不锁中间内容。
- 段提示词模式：只要有一段写了提示词，所有段都必须写；全部留空时复用 `globalPrompt`。单段模式（`count = 0`）必须有 `globalPrompt`。
- 生产判断：单次 5–15 秒内的切镜写进同一条 prompt 的 `[Shot N]`；只有同一条连续动作超过单次 15 秒上限，才用正重叠拆段。**0 重叠只适合无需继承的段，不要用它把无关镜头串成长链。**

## 10. 画质与性能参数

- **`ref_image_size`**：`match` 把参考图按生成画面的像素面积等比缩小（不放大），速度快；`max` 用参考管线的 2048 短边，身份保真最好，但参考 token 参与每一步采样，可能慢数倍。主角特写和身份敏感镜头用 `max`，群像与空镜用 `match`。
- **画布**：宽高都是 32 的倍数；参考视频单独降分辨率可显著省算力。
- **SelfLift 二采**：开启 `secondPass`，`secondPassModel` 填 `latent_upscale_models` 目录中的 H3 Latent Upscaler，`secondPassHighSteps` 取总步数的约 25%（如 8 步填 2），必须大于 0 且小于总步数；采样器必须是标准 `euler`（`s_churn` 为 0）。二采在低清和高清两层都做段间续接，长视频不会逐段反复编解码而劣化。
- **低内存版本**：内存紧张或超长成片时改用；每段解码后立即编码为临时视频并释放帧内存。保留二采和重叠去重，但不保存 latent checkpoint，只有末段 latent 输出，也没有单段重跑。临时片段是 H.264 CRF 18，最终再合并；对代际压缩敏感时用内存版。
- **帧内存**：默认合并帧留在内存；需要时设置 `H3_MERGED_FP16=1` 减半保留字节，或用低内存版本。
- 先用 2–3 段、低分辨率验证整条计划，再放大到正式规格。

## 11. 预设与复现

导出预设有两种：`configuration` 只存素材编排、提示词、分段、音频锁定与二采开关；`complete` 另把引用的媒体复制进同一预设目录，可整体迁移到另一台机器。预设**不记录**模型、LoRA、插件版本、ComfyUI 版本与采样参数，所以复现依据必须写进本 Skill 的生产台账：插件 commit、模型与 LoRA 文件、采样器、步数、种子、画布、`ref_image_size`，以及计划检查报告的哈希。

## 12. 与本 Skill 门禁的衔接

1. 提交前对实际 `timeline_data` 运行 `scripts/timeline_plan_check.py`。输入 JSON 包含 `timeline_data`，可选 `runtime`（`finite_segment` 默认，或 `director` 表示兼容导演台）、`width`、`height`、`generation_seconds`、`prompt`（兼容导演台的节点提示词）、`audio_intent`（`generate`/`locked_audio`/`video_original`/`silent`）、`sampler`（`{name, steps}`）、`prompt_index`、`planner_output`（`material`/`segment`）与 `inject_continuity_instruction`。报告给出逐段标签清单、Guide 帧、音频路由、保留帧数与问题清单；`block` 必须修，`review` 要有证据。
2. 每段提示词照常过 `context_ir_check.py` 与 `prompt_preflight.py`；把计划检查给出的该段标签清单作为附件绑定的依据。
3. **一次执行与逐段把关的取舍**：一键采样器一次跑完，中途不能停、不能单段重跑；低内存版同样没有单段重跑。原生 Loop 节点组可以在循环体里插入预览、保存或自定义处理，逐段观察，失败时停在当前段下游之前；它仍没有磁盘片段缓存和选择性单段重跑。长镜续写、单场景、低风险段落用一键采样器，生成后按 [segment-seam-continuity.md](segment-seam-continuity.md) 逐个接缝复核；有台词、多人、高风险段落用原生 Loop 逐段看，或逐段独立生成——每段合格后把成片作为下一段的 `guide` 片段，合并时按计划检查报告的 Guide 帧数同时删掉视频和音频的重复部分。后者会失去 latent 续接，接缝质量不如同一次有限分段。
4. `Prompt Index` 只给 `Material Plan` 按段过滤素材；一键采样器的 `Segment Plan` 不接受它。要逐段材料过滤，用 Material Plan + 单段生成，或原生 Loop 的选择循环分段。
5. `scripts/submission_gateway.py` 目前只认兼容导演台的单节点工作流图；有限分段工作流图要等适配器核实后再接入网关，在此之前提交记录标记该路线 `unverified`，并以计划检查报告和台账作为证据。
6. 生成后用 `scripts/media_qc.py` 测时长、黑帧、冻结和响度；有限分段的成片时长应等于报告的 `target_output_frames / 24`。低内存版本没有 latent checkpoint，不能用末段 latent 继续整片。

## 13. 静默陷阱速查

| 情况 | 插件行为 | 计划检查代码 |
|---|---|---|
| 规划台接的是 `Material Plan` 而不是 `Segment Plan` | Material Plan 已被 `activeIndex`/`prompt_index` 过滤，有限分段采样报 `Disconnect Prompt Index when generating all timeline segments` | `MATERIAL_PLAN_OUTPUT`（需在检查输入声明 `planner_output: "material"`） |
| 接 `Segment Plan` 时 `Prompt Index` 仍连着 | 规划器输出带 `prompt_index`，有限分段采样报错 | `PROMPT_INDEX_CONNECTED` |
| 以为主规划路径会自动注入续写说明 | 不会；只有已弃用的 Finite Segment Expansion 有 `inject_continuity_instruction` | `CONTINUITY_INJECTION_LEGACY_ONLY` / `CONTINUATION_SHOT1_REVIEW` |
| 视频片段没写 `referenceMode` | 按 `guide` 逐帧锁定（界面新上传默认却是 `edit`） | `REFERENCE_MODE_IMPLICIT` |
| `referenceMode` 拼错 | 静默变成 `guide` | `REFERENCE_MODE_INVALID` |
| 没写 `hasAudio` / `videoAudioEnabled` | 当作 true，原声可能锁死最终音轨 | `CLIP_AUDIO_IMPLICIT` / `VIDEO_AUDIO_IMPLICIT` |
| 每段超过 9 图 / 3 视频窗口 / 3 音频 | 超出部分静默丢弃 | `SEGMENT_CAPACITY_EXCEEDED` |
| 段内素材 id 写错 | 静默丢弃 | `SEGMENT_ASSET_UNKNOWN` |
| 视频与生成区相交不足 5 帧 | 不作参考；清单与编码器可能错位 | `VIDEO_INTERSECTION_TOO_SHORT` |
| 提示词引用了该段不存在的编号 | 绑定落空 | `PROMPT_LABEL_OUT_OF_RANGE` |
| 续写段没有 `[Shot 1]` | 新剧情与固定画面冲突 | `CONTINUATION_SHOT1_MISSING` |
| 段长超过 362 帧 | 插件接受，但超出 H3 训练区间，质量未验证 | `SEGMENT_OUTSIDE_TRAINED_RANGE` |
| 段长超过 3592 帧或不在 `5+17n` 网格 | 报错 | `SEGMENT_LENGTH_OFF_GRID` |
| `count=0` 单段没写 `globalPrompt` | 报错 | `PROMPT_MISSING` |
| 想要生成声音却带着有声参考视频 | 最终音轨被原声替代 | `AUDIO_ROUTE_FIXED` / `AUDIO_ROUTE_MISMATCH` |
| 锁定音轨只分给部分段 | 报错停止 | `LOCKED_AUDIO_PARTIAL` |
| 锁定音轨/静音时仍开 `continue_audio_latent` | 音频续接被绕过，最终整轨替换 | `AUDIO_ROUTE_FIXED`（review） |
| 把 `Last Sampled Latent` 当整条长视频 latent | 它只是最后一段的 latent | 对照计划报告的 `target_output_frames` |
| 用一键采样器或低内存版做单段重跑 | 没有这个能力 | 用原生 Loop 或逐段生成 |
| 二采用了非 euler 采样器 | 报错停止 | `SECOND_PASS_SAMPLER` |
| 二采用了非 H3 latent upscaler | 报错停止 | `SECOND_PASS_MODEL_MISSING` |

## 来源

- [ComfyUI-MiniMaxH3-TimelineDirector](https://github.com/Songssx/ComfyUI-MiniMaxH3-TimelineDirector)（GPL-3.0），含长视频 Agent 操作规范与有限分段说明；行为按 commit `050226d` 源码核实。
- [MiniMax H3 官方提示词规范](https://github.com/MiniMax-AI/MiniMax-H3/blob/main/skills/h3-prompt-writing/references/ref-en.txt)。
