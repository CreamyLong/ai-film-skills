# MiniMax H3 时间线导演台（TimelineDirector）运行时适配

目标运行时是 ComfyUI + `ComfyUI-MiniMaxH3-TimelineDirector` 插件时读本文件。它是 H3 Ref2VA 路线下的**运行时适配层**：提示词仍按 [context-ir-format.md](context-ir-format.md) 的六段结构写，本文件说明怎样把素材、分段、音频与参数交给这个插件，并把它的全部能力用足。

本文行为按插件 commit `050226d`（2026-10）源码核实；插件升级后先重跑 `scripts/timeline_plan_check.py` 的回归并复核第 7、8、13 节，未核实的新行为按 [provider-shells.md](provider-shells.md) 记为 `unverified`。插件为 GPL-3.0，本文只描述行为，不复制其文档或代码。

## 1. 它解决什么、什么时候用

H3 单次推理只能出 4–15 秒，参考素材每次最多 9 图、3 段视频、3 段音频、合计 12 个。插件解决五件事：

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
| 单镜 >15 秒的连续镜头、整场多镜一次出、长时长数字人 | 本插件有限分段 |

## 2. 节点与工作流怎么选

| 节点/工作流 | 什么时候用 |
|---|---|
| **素材规划台 → 有限分段采样**（默认） | 一切新工作。规划台的「分段规划」直接接采样器的「有限分段规划」；单段、多段、文生、参考生都用同一张图 |
| **有限分段采样（低内存版本）** | 长时长或高分辨率：每段解码后立即编码为临时视频并释放帧内存，直接输出 `VIDEO` 给保存节点；不输出 latent，不支持单段重跑 |
| **原生 Loop 节点组**（初始化/选择/准备/合并/完成分段循环） | 需要在每段之间插入自定义处理、预览或保存时；依赖 ComfyUI 原生 `Start Loop / End Loop` |
| **Omni 素材包提示词桥** | 让多模态提示词重写器先读完有序素材再写 H3 提示词；需另装 Prompt Rewriter Omni。重写结果仍要按本 Skill 预检，不能直接视为合格提示词 |
| **时间线导演台（兼容）** | 旧的一体化单段节点：自带 `prompt` 输入，只渲染一个时间窗，不支持分段与原音锁定 |
| **导出预设 / 本地预设加载器** | 保存与复用素材编排（第 11 节） |

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
| 一场多镜一次出 | 每段各自的图片/音频 | — | H3 生成 | 时间框 0 重叠 = 硬切；每段一条完整提示词 |
| 接上一次已生成的成片 | 上一段成片作视频片段，盖住生成区开头 | `guide` | 要新声音必须 `hasAudio: false` | `[Shot 1]` 先描述固定 Guide 中的画面 |

## 4. 素材导入

- 所有素材必须位于 ComfyUI 的 input 目录之下，计划里写相对路径；目录外的路径会被拒绝。界面上传的文件落在插件自己的子目录里，API 提交时同样写相对 input 目录的路径。
- 全局素材库不限数量；每段实际可用最多 9 张图、3 段视频窗口、3 段参考音频，合计不超过 12（含视频原声）。
- 图片解码时按画布 `width × height` 适配；每段视频可单独设 `referenceWidth/referenceHeight`（对齐到 32），降低参考 latent 计算量而不改变成片画布。
- 分段时图片和音频按 **id** 分配给各段，不按列表位置；删除或重排全局素材库不会让某段悄悄换文件，但写错的 id 会被静默丢弃。

## 5. `timeline_data` 字段

| 位置 | 字段 | 含义 |
|---|---|---|
| 顶层 | `selection.start/duration` | 生成区（秒）。未分段时就是本次生成窗口 |
| 顶层 | `images[]` | `{id, file, name}`；顺序即未分段时的 `<Picture N>` 顺序 |
| 顶层 | `audios[]` | `{id, file, name, audioMode, trimStart, duration}`；`audioMode` 为 `reference` 或 `locked` |
| 顶层 | `videoClips[]` | `{id, file, name, start, duration, trimStart, hasAudio, referenceMode, referenceWidth, referenceHeight}`；`start` 是时间线位置，`trimStart` 是源文件入点 |
| 顶层 | `videoAudioEnabled` | 参考视频原声总开关；决定锁定、静音还是生成（第 7 节） |
| 顶层 | `globalPrompt` | 全局提示词：未分段时使用；分段且没有任何段落提示词时复用于每段 |
| 顶层 | `secondPass / secondPassModel / secondPassHighSteps` | 二采开关、Latent Upscaler 文件名、高清步数 |
| 顶层 | `segmentConfig` | `{count, mode: "timeline", segments[]}`；`count` 为 0 时不分段 |
| 每段 | `startFrame / endFrame` | 整数帧（24 fps），时间线全局坐标 |
| 每段 | `images[] / audios[]` | 该段使用的素材 id，顺序即该段内的标签顺序 |
| 每段 | `prompt` | 该段完整的六段式提示词 |

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

## 8. 标签编号规则

- `<Picture N>`：该段图片按顺序从 1 编号（未分段时用全局顺序）。
- `<Video N>`：与该段生成区相交的视频窗口，按时间线从左到右编号。
- `<Audio N>`：先编该段的独立参考音频（锁定音轨不编号），再接各视频窗口的配对原声（仅当原声启用）。
- 分段后每段都从 1 重新编号；全局计划用全片镜头号，提示词内用段内编号，两者映射要记录。
- 规划台输出的 Omni 素材包里带有与编码器一致的标签清单；提交前用 `scripts/timeline_plan_check.py` 离线得到同样的逐段清单并核对提示词。

## 9. 分段、重叠与段提示词

- 每段长度必须是 `5 + 17n` 帧，最多 3592 帧；但 H3 训练范围约 124–362 帧（5–15 秒），超出范围插件照跑，质量未经验证，按复核项处理。
- 段数 1–64；第一段从第 0 帧开始；后段起点和终点都要前进，段间不能有空隙。
- 重叠 = 上一段终点 − 本段起点，只能是 0、1 或 `5 + 17n`（5、22、39、56…），且短于相邻两段。0 是剪辑硬切；正重叠启用 latent 续写。旧的有限扩展节点会把重叠向下取整（24→22，48→39），时间框路径则直接拒绝非法值。
- 重叠时长按动作选：静态镜头取 5 或 22 帧；动作、运镜或跨段对白取 22–39 帧（约 0.9–1.6 秒），覆盖动作趋势与语气。不要把接缝放在嘴型中间、快速闪切或最模糊的一帧。
- **续写段的 `[Shot 1]` 必须先复述重叠区里已经存在的画面**（人物位置、动作相位、机位、光线、正在持续的声音），再写重叠结束后的发展；重叠后若本该切镜，新镜头从切点写成 `[Shot 2]`。主路径（规划台 → 有限分段采样）不会替你注入这段说明。
- 段提示词模式：只要有一段写了提示词，所有段都必须写；全部留空时复用 `globalPrompt`。
- 每段实际贡献的新帧 = 段长 − 重叠；成片总帧数 = 最后一段的终点帧。

## 10. 画质与性能参数

- **`ref_image_size`**：`match` 把参考图按生成画面的像素面积等比缩小（不放大），速度快；`max` 用参考管线的 2048 短边，身份保真最好，但参考 token 参与每一步采样，可能慢数倍。主角特写和身份敏感镜头用 `max`，群像与空镜用 `match`。
- **画布**：宽高都是 32 的倍数；参考视频单独降分辨率可显著省算力。
- **SelfLift 二采**：开启 `secondPass`，`secondPassModel` 填 `latent_upscale_models` 目录中的 H3 Latent Upscaler，`secondPassHighSteps` 取总步数的约 25%（如 8 步填 2），必须大于 0 且小于总步数；采样器必须是标准 `euler`（`s_churn` 为 0）。二采在低清和高清两层都做段间续接，长视频不会逐段反复编解码而劣化。
- **低内存版本**：内存紧张或超长成片时改用，代价是失去 latent 输出和单段重跑。
- 先用 2–3 段、低分辨率验证整条计划，再放大到正式规格。

## 11. 预设与复现

导出预设有两种：`configuration` 只存素材编排、提示词、分段、音频锁定与二采开关；`complete` 另把引用的媒体复制进同一预设目录，可整体迁移到另一台机器。预设**不记录**模型、LoRA、插件版本、ComfyUI 版本与采样参数，所以复现依据必须写进本 Skill 的生产台账：插件 commit、模型与 LoRA 文件、采样器、步数、种子、画布、`ref_image_size`，以及计划检查报告的哈希。

## 12. 与本 Skill 门禁的衔接

1. 提交前对实际 `timeline_data` 运行 `scripts/timeline_plan_check.py`。输入 JSON 包含 `timeline_data`，可选 `runtime`（`finite_segment` 默认，或 `director` 表示兼容导演台）、`width`、`height`、`generation_seconds`、`prompt`（兼容导演台的节点提示词）、`audio_intent`（`generate`/`locked_audio`/`video_original`/`silent`）与 `sampler`（`{name, steps}`）。报告给出逐段标签清单、Guide 帧、音频路由、保留帧数与问题清单；`block` 必须修，`review` 要有证据。
2. 每段提示词照常过 `context_ir_check.py` 与 `prompt_preflight.py`；把计划检查给出的该段标签清单作为附件绑定的依据。
3. **一次执行与逐段把关的取舍**：有限分段一次跑完，中途不能停下检查，也不能只重跑一段。长镜续写、单场景、风险低的段落用它，生成后按 [segment-seam-continuity.md](segment-seam-continuity.md) 逐个接缝复核；有台词、多人、高风险的段落改为逐段生成：每段合格后把成片作为下一段的 `guide` 片段，合并时按计划检查报告的 Guide 帧数同时删掉视频和音频的重复部分。
4. `scripts/submission_gateway.py` 目前只认兼容导演台的单节点工作流图；有限分段工作流图要等适配器核实后再接入网关，在此之前提交记录标记该路线 `unverified`，并以计划检查报告和台账作为证据。
5. 生成后用 `scripts/media_qc.py` 测时长、黑帧、冻结和响度；有限分段的成片时长应等于报告的 `target_output_frames / 24`。

## 13. 静默陷阱速查

| 情况 | 插件行为 | 计划检查代码 |
|---|---|---|
| 视频片段没写 `referenceMode` | 按 `guide` 逐帧锁定（界面新上传默认却是 `edit`） | `REFERENCE_MODE_IMPLICIT` |
| `referenceMode` 拼错 | 静默变成 `guide` | `REFERENCE_MODE_INVALID` |
| 没写 `hasAudio` / `videoAudioEnabled` | 当作 true，原声可能锁死最终音轨 | `CLIP_AUDIO_IMPLICIT` / `VIDEO_AUDIO_IMPLICIT` |
| 每段超过 9 图 / 3 视频窗口 / 3 音频 | 超出部分静默丢弃 | `SEGMENT_CAPACITY_EXCEEDED` |
| 段内素材 id 写错 | 静默丢弃 | `SEGMENT_ASSET_UNKNOWN` |
| 视频与生成区相交不足 5 帧 | 不作参考；清单与编码器可能错位 | `VIDEO_INTERSECTION_TOO_SHORT` |
| 提示词引用了该段不存在的编号 | 绑定落空 | `PROMPT_LABEL_OUT_OF_RANGE` |
| 续写段没有 `[Shot 1]` | 新剧情与固定画面冲突 | `CONTINUATION_SHOT1_MISSING` |
| 想要生成声音却带着有声参考视频 | 最终音轨被原声替代 | `AUDIO_ROUTE_FIXED` / `AUDIO_ROUTE_MISMATCH` |
| 锁定音轨只分给部分段 | 报错停止 | `LOCKED_AUDIO_PARTIAL` |
| 二采用了非 euler 采样器 | 报错停止 | `SECOND_PASS_SAMPLER` |

## 来源

- [ComfyUI-MiniMaxH3-TimelineDirector](https://github.com/Songssx/ComfyUI-MiniMaxH3-TimelineDirector)（GPL-3.0），含长视频 Agent 操作规范与有限分段说明；行为按 commit `050226d` 源码核实。
- [MiniMax H3 官方提示词规范](https://github.com/MiniMax-AI/MiniMax-H3/blob/main/skills/h3-prompt-writing/references/ref-en.txt)。
