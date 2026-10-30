# H3 基础模式提示词格式（T2VA / I2VA / FL2VA / L2VA）

## 适用条件

目标模型或节点采用 MiniMax H3 基础模式（不带全参考绑定）时使用本格式：文生视频（T2VA）、首帧生视频（I2VA）、首尾帧生视频（FL2VA）、尾帧生视频（L2VA）。有需要逐标签追踪的引用素材关系时改用 [context-ir-format.md](context-ir-format.md) 的六段全参考结构；两种外壳承载同一批导演决定，不能混写。格式来源为 MiniMax 官方 H3 Prompt Writing Guide 基础篇；本文件只保留结构与标记规则，不复制官方示例。

## 三段核心字段

所有基础模式共用三个字段，按顺序输出：

```text
integrated_multimodal_description: [Shot 1] ...

overall_soundscape: ...

non_diegetic_music: ...
```

- `integrated_multimodal_description`：沿时间轴写画面、动作、镜头、说话人、台词与同期声，是提示词主体。
- `overall_soundscape`：1–4 句概括全片环境声、动作音和非言语人声；台词与同期音乐已写进正文，不在这里重复；用户明确要求全片静音时才写 `N/A`。
- `non_diegetic_music`：1–3 句写只有观众能听到的配乐的乐器、速度、节奏与动态变化；没有时写 `N/A`。

## 首行模式指令

T2VA 没有图像对齐指令，正文直接从 `integrated_multimodal_description:` 开始。其余三种模式的第一行固定为对齐指令，之后空一行再写三个核心字段：

| 模式 | 首行 |
|---|---|
| I2VA | `For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.` |
| FL2VA | `How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot N) aligns with the S.SS-second mark of the target video.` |
| L2VA | `How the reference pictures align with the target video — <Picture 1> (from [Shot N]) aligns with the S.SS-second mark of the target video.` |

其中 `N` 是实际最后一个镜头的编号，`S.SS` 是有效视频时长、精确到两位小数。首行是指令不是镜头正文，不参与 `[Shot N]` 编号。

## 各模式的图像职责

- **I2VA**：`<Picture 1>` 是 0 秒处的真实首帧，属于 `[Shot 1]`。正文先建立图中的风格、主体、构图与场景锚点，再写动作如何向前发展；人物身份、服装、颜色、关键物件与空间关系保持与图一致。
- **FL2VA**：Picture 1 是开头、Picture 2 是结尾，正文写两端之间的连续运动路径，一般只用单镜头让模型从首帧插值到末帧；只有明确要求多镜时才切镜，末帧必须在最后一个 `[Shot N]` 末尾到达。
- **L2VA**：`<Picture 1>` 是最后一帧，属于最后的 `[Shot N]`，不天然属于 Shot 1；正文先推一个合理的前态，再让人物、物件、摄影机与场景逐步收束到参考图。
- **T2VA**：无参考图，按文本构建完整时间轴；补写的场景、人物、动作与声音细节必须与用户意图一致。

## 与全参考格式共享的正文标记

- `[Shot 1]` 为首镜不带时间戳；后续镜头写 `[Shot N] At MM:SS.mmm, ...`，切点递增且在总时长内。
- 摄影机运动按"运动类型＋幅度＋速度"写成自然语句（如 `pushes in with small amplitude at slow speed`），不堆叠标签；常规幅度与速度省略。
- 说话人 `(S1)`、`(S2)` 按实际发声顺序编号，跨镜复用；多人同时发声写 `(S1,S2)`；不发声的角色不给编号。首次出现时用画面与声音上下文（年龄、性别、是否在画内、音高、音色、语速、口音）建立稳定身份；身份短语、编号、动作与发声方式写在 `<d>` 外。
- 台词与歌词写 `<d>[语言] 原文</d>`，逐字保留原文语言与标点，不翻译不改写；画外音用 `says in an off-screen voiceover`，并在每个画外音 `<d>` 之后写明画面中该角色嘴唇保持闭合。
- 台词跨切点时两侧都写 `<scenetrans>` 并注明声音延续；台词被视频结尾截断时用 `<cutoff>`。
- 画面中实际可见的横幅、招牌、字幕、霓虹等文字用英文双引号逐字保留。

## 标签边界

- 基础模式只使用 `<Picture N>`（关键帧锚点），按首帧、末帧等实际图顺序编号；`<Subject N>`、`<Video N>`、`<Audio N>` 属于全参考格式，不出现在基础模式提示词中。
- T2VA 不出现任何 `<Picture N>`；I2VA 与 L2VA 各一张、FL2VA 两张，编号与实际附件顺序一致。
- 声音没有 `<Audio N>` 绑定；音色与发声方式只能在正文与声景字段里描述。

## 编译边界

- 本格式只组织已确定的导演决定，不新增人物、事件、动作、台词或音乐。
- 结构完整不证明画面、音色或剧情合格；生成后仍须看实际片段。
- 运行 `scripts/h3_base_check.py`（或经 `prompt_preflight.py` 声明 `prompt_format: "h3_base"` 加 `h3_mode`）核对结构，结构通过不等于提交许可。

## 参考

- [MiniMax H3 Prompt Writing Guide（Base: T2VA / I2VA / FL2VA / L2VA）](https://github.com/MiniMax-AI/MiniMax-H3/blob/main/skills/h3-prompt-writing/references/base-en.txt)
