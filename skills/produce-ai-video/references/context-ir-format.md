# H3 Context-IR 结构化提示词格式

## 适用条件

目标模型或节点采用 MiniMax H3 Context-IR 全参考格式（Ref2VA）时使用本格式。其他模型按其已核实格式转写，不把本格式当作所有 H3 路线的事实。格式来源为 MiniMax 官方 H3 Prompt Writing Guide；本文件只保留结构与标记规则，不复制官方示例。

## 六段结构

按顺序输出六段，段名固定：

| 段 | 内容 |
|---|---|
| `subject_definitions` | 定义每个需要单独追踪的引用内容及其标签 |
| `summary` | 一段话说明任务类型与主要引用关系，开头带方括号任务类型 |
| `retention_analysis` | 逐项说明引用内容如何被保留、转移、复制或弱引用 |
| `detailed_description` | 按播放顺序逐镜描述画面、动作、声音与台词 |
| `overall_soundscape` | 全片环境声与物理声音 |
| `non_diegetic_music` | 只有观众能听到的背景音乐；没有时写 `N/A` |

任务类型按引用素材的实际作用选择，可组合：`keyframe completion`（图作具体帧锚点）、`reference generation`（素材只提供生成指引）、`video editing`（直接修改源视频）、`video continuation`（从源视频续接）、`audio reuse`（直接复用音频信号）、`audio reference`（只参考音色、节奏或风格）。

## 四种引用标签

| 标签 | 定义 | 不用于 |
|---|---|---|
| `<Subject N>` | 从参考素材抽象出的可复用可见内容：人物、场景、服装、道具、界面、动作、姿势 | 不代表源文件本身 |
| `<Picture N>` | 作为具体帧锚点的参考图：首帧、关键帧、尾帧、分镜规划图 | 只用来定义人物或风格时不单独建条目，写进对应 Subject 的定义 |
| `<Video N>` | 整段视频关系：剪辑源、续接起点、时间结构 | 视频里的人物或物件仍用 Subject |
| `<Audio N>` | 被复制或引用的音频信号：音色、节奏、台词内容、音效质感 | 普通参考视频自带声音不自动建 Audio 条目 |

规则：

- 标签一经分配，在六段中含义不变；每类独立编号。
- 一个 Subject 可由多个素材定义，一个素材也可提供多个 Subject。
- 音频对应说话人时写 `<Subject N> (Sx)` 或稳定声音描述加 `(Sx)`，编号与正文说话人顺序一致，不另行编号。

## 关系标记

`retention_analysis` 每行一个标签，格式为 `<标签> (出现位置): 标记 - 说明`。

可见内容（Subject、Picture、Video）：

| 标记 | 含义 |
|---|---|
| `fully_preserved` | 定义的职责完全保留 |
| `partially_preserved` | 仍在使用，但部分特征改变 |
| `attribute_transfer` | 特征转移到另一个可识别主体 |
| `weak_reference` | 只保留风格、类别或氛围等大类相似 |

音频（Audio）：

| 标记 | 含义 |
|---|---|
| `fully_copy` | 完整复制为最终音轨 |
| `partially_copy` | 部分复制，或复制后增删替换 |
| `reference` | 只参考音色、节奏、风格或内容，不复制信号 |
| `weak_reference` | 只保留大类氛围 |

关系标记只能在该标签已定义的职责范围内选择；新增的动作、背景或剧情不算引用保真损失。

## 镜头与台词标记

`detailed_description` 正文规则：

- `[Shot 1]` 为首镜，不带时间戳；后续镜头写 `[Shot N] At MM:SS.mmm, ...` 给出切点时间，切点递增且在总时长内。
- 每个镜头写清构图、主体外观与位置、环境与光线、动作与状态变化、摄影机运动、当前声音，以及引用内容实际出现的位置。
- 说话人用 `(S1)`、`(S2)` 按实际发声顺序编号，跨镜复用；主体说话时写 `<Subject N> (Sx)`，画外音注明 off-screen 且嘴唇不动。
- 台词与歌词写 `<d>[语言] 原文</d>`，保留原文语言与逐字内容；听不清的片段写 `[unclear]`，不猜测改写。
- 台词跨切点时，两侧都写 `<scenetrans>` 并注明声音延续；台词被视频结尾截断时用 `<cutoff>`。
- 引用标签在首次清晰出现处写入，后续镜头复用同一标签，不重新定义。

## 编译边界

- 本格式只组织已确定的导演决定，不新增人物、事件、动作、台词或音乐。
- 参考图超出模型容量时拒绝，不截断；标签与附件的对应关系按 [production-ledger.md](production-ledger.md) 的提交记录核对。
- 台词逐字保留仍按 [shot-audit-protocol.md](shot-audit-protocol.md) 对照源对白；本格式不证明台词已进入实际提交。
- 结构完整不证明画面、音色或剧情合格；生成后仍须看实际片段。

## 参考

- [MiniMax H3 Prompt Writing Guide（Full-Reference）](https://github.com/MiniMax-AI/MiniMax-H3/blob/main/skills/h3-prompt-writing/references/ref-en.txt)
- [MiniMax H3 Context-IR API](https://platform.minimax.io/docs/api-reference/video-generation-v2-h3-context-ir)
