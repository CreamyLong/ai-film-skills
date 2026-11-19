# FFmpeg 组装与后期工具合同

本文件是成片组装和后期的运行时合同。它把 FFmpeg 当作**执行后端**，不要求作者手写滤镜图：作者交付 EDL、参数规格和验收项，组装器把它们翻译成受控的 FFmpeg 操作。灵感来自公开的 agent 视频工具实践（`kajisho5/ffmpeg-skill`、`jianshuo/claude-skills`、MoneyPrinterTurbo，均为 MIT 或公开实现）；下面是本包自己的规则与命令写法，不复制其代码。

## 0. 硬规则

1. **先 probe，后决策。** 不看文件名猜分辨率、帧率、声道或编码；所有参数从实际流读取。
2. **先归一化，再拼接。** 分辨率、SAR、像素格式、帧率、颜色矩阵、音频采样率与声道布局必须在拼接前统一；不允许把不同规格直接 `concat -c copy`。
3. **最终只编码一次。** 中间步骤用无损或高质量中间格式；字幕、混音、调色尽量在同一遍最终编码完成，不做级联重编码。
4. **不覆盖输入。** 输出先写临时文件，完成后再原子改名；已有输出默认拒绝覆盖，除非显式授权。
5. **调用方不传滤镜字符串。** Agent 只选择操作和参数（裁剪、拼接、混音、烧字幕、导出），滤镜图由工具内部生成并校验；禁止把用户文本拼进 `-vf`/`-filter_complex`。
6. **结果必须复测。** 输出后重新测时长、分辨率、帧率、音频响度/峰值、解码是否完整；抽帧与波形只能证明机械属性，不能证明表演、构图或混音平衡。
7. **镜头之间不做叠化。** 场景内硬切；场景之间用淡黑，不是两个画面半透明叠加。声音可以在切点做 2–3 帧等功率交叉，但不能重复对白。
8. **烧录字幕只来自已批准文本。** 不使用模型在画面里自创的字幕；字幕用 libass/ASS 一次烧入，字体与断句走已审版本。

## 1. 能力地图

| 类别 | 操作 | 用途 |
|---|---|---|
| 分析 | `probe`、`scenes`、`look`、`waveform` | 读流参数、场景切点、抽帧、波形；不做内容判断 |
| 剪辑 | `cut`、`join`、`fit`、`crop`、`pad`、`insert`、`freeze`、`loop`、`speedramp`、`sequence` | 精确切点、拼接、适配画布、插入、冻结、变速、按 EDL 排序 |
| 音频 | `audio`、`sync`、`loudness`、`mix` | 提取/替换/重采样、音画同步、响度、总线混音 |
| 画面 | `caption`、`overlay`、`graphics`、`color`、`grid` | 字幕、叠加、图形、色彩转换、联系表 |
| 交付 | `export`、`proxy`、`check`、`report` | 导出、代理、机械检查、报告 |
| 编排 | `render`、`batch`、`verify` | 单条渲染、批量、复测 |

本包不要求实现全部操作，但组装器至少要覆盖：probe、conform、cut、join、audio mix、loudness、caption、export、check。

## 2. 参数一致性合同

### 2.1 必须统一的字段

| 层 | 字段 | 目标示例 |
|---|---|---|
| 画面 | width、height、pixel format | 768×1344、yuv420p |
| 画面 | sample aspect ratio (SAR) | 1:1 |
| 画面 | frame rate、timebase | 24/1、1/12288 或统一 timebase |
| 画面 | color primaries / transfer / matrix / range | bt709 / bt709 / bt709 / tv |
| 编码 | codec、profile、level | H.264 High、AAC-LC |
| 音频 | sample rate、channels、layout | 48000 Hz、2、stereo |
| 音频 | codec、bitrate | AAC、192k |
| 容器 | rotation、timestamps | 无旋转、从 0 开始 |

### 2.2 不一致的症状

- 拼接直接失败，或只有第一段能播。
- 分辨率/SAR 不一致：拉伸、黑边、画面比例错。
- 帧率不一致：变速、音画漂移、重复/丢帧。
- 颜色标签不一致：偏色、发灰、对比度跳变。
- 音频采样率/声道不一致：变调、单声道塌陷、爆音。
- timebase 或 rotation 不一致：时间戳错乱、竖屏变横屏。

### 2.3 统一方式

- 每个片段先 conform 到目标规格，再 concat；conform 用一次重编码，不复用源参数。
- 提交前运行 `scripts/ffmpeg_conform_check.py`；任何 BLOCK 项先修，不进入拼接。
- 源片段只读；conform 产物写独立目录，保留原文件以便回溯。

## 3. 拼接

### 3.1 选择

| 情况 | 方法 |
|---|---|
| 所有片段已严格同规格、同编码、同 timebase | concat demuxer + `-c copy`（最快） |
| 规格有差异、需要重编码 | concat filter，或先 conform 再 demuxer |
| 需要音频交叉淡化但视频硬切 | 逐段裁剪视频尾部 + 音频 `acrossfade`，见 3.3 |
| 场景之间 | 视频 `fadeblack` 0.2–0.3 s + 音频 `acrossfade`，不是叠化 |

### 3.2 受控命令形态

```bash
# 只读探测
ffprobe -v error -show_streams -show_format -of json input.mp4

# conform 到目标规格（示例）
ffmpeg -y -i in.mp4 \
  -vf "scale=768:1344:force_original_aspect_ratio=increase:out_color_matrix=bt709:out_range=tv,crop=768:1344,fps=24,setsar=1,format=yuv420p,setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv" \
  -af "aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo" \
  -c:v libx264 -crf 17 -preset medium -pix_fmt yuv420p \
  -c:a aac -b:a 192k conformed.mp4
```

### 3.3 音频平滑而不叠化

视频保持硬切，只让声音过渡：

- 前一段视频尾部裁掉 `d` 帧，音频保留完整；
- 相邻段音频用 `acrossfade=d=2/24` 等功率交叉；
- 总时长两边同时减少 `d`，音画不错位；
- `d` 取 2–3 帧（83–125 ms），不要再长，否则会吃掉句尾辅音；
- 不允许用重复对白或保留重叠画面来“盖住”接缝。

## 4. 声音

### 4.1 电平与响度

- `mean_volume`（ffmpeg `volumedetect`）是平均 dBFS，快但非感知响度；用于逐段快速拉平。
- `loudnorm`（EBU R128）给出 integrated LUFS、true peak、LRA；用于交付规格和跨集统一。
- 建议：逐段先用 mean_volume 拉到同一目标（如 −23 dB），整片再用 loudnorm 或 limiter 收到交付目标。
- 峰值不得高于 −1 dBTP；需要 limiter 时放在最终总线，不在每段重复压。
- 逐镜目标要分类型：对白镜统一到对话电平（如 −19 dB），环境/反应镜统一到更低的环境电平（如 −30 dB）；不要全片一个 `volume=0.9`。
- 每个镜头首尾各加 20 ms `afade`，消除硬切爆音；这不是叠化，不改变画面。
- 静帧的 `tone_from` 必须指向无对白镜；指向对白镜会把那句台词以低音量重放一遍（鬼声）。
- 逐镜电平和切点跳变的检查见 `scripts/audio_continuity_check.py` 与 `audio-continuity.md`；同场对白切点差应 ≤3 dB。

### 4.2 混音

- 对白、环境、音效、音乐分轨；对白优先，环境让位，音乐只在授权时加入。
- 混音用 `amix normalize=0`，否则 ffmpeg 会自动把每路除以输入数，整体掉 6 dB。
- 对白轨做轻降噪/去齿音前先保留原始干声；不要在未审听的情况下重压动态。
- 原生对白、后期配音、OS 台词只能选一条主路线，不能叠同一句。

### 4.3 多段生成内部的 Soft AV

- 有限分段 `overlap>0` 时，插件自己用上一段音频 latent 尾部 + 最后 8 个 tick 的半余弦释放做接缝；合并时裁前段尾部。
- 这是**同一次多段生成内部**的机制，不适用于独立镜头之间的后期拼接；独立镜头用 3.3 的音频交叉。

## 5. 静帧与运动

- 静帧插入用 `loop` + `zoompan`，时长按帧数精确计算；不要把静帧写成视频再抽帧。
- 静帧要有轻微推拉（如 1.0→1.05），否则观感是幻灯片。
- 信息型道具（证件、屏幕、车票、信封）一律静帧或后期文字板，不让视频模型生成可读文字。

## 6. 字幕

- 字幕文本来自已批准 SRT/ASS；不让模型在画面里自创字幕。
- 烧录用 libass（`.ass`）或 `drawtext`；中文用明确字体文件，避免方框。
- 字幕、混音、最终编码尽量同一遍完成；不要先烧字幕再重新编码混音。
- 发现模型烧录字幕时，按 `keyframe-visual-review.md` 的处置：重跑、裁掉可安全裁掉的区域，或改静帧/OS；不要用涂抹掩盖。

## 7. 机械检查

| 检查 | 工具 | 判定 |
|---|---|---|
| 流与时长 | ffprobe | 分辨率、帧率、时长、音轨存在 |
| 解码完整 | ffmpeg `-f null -` | 无错误 |
| 黑帧/冻结 | `blackdetect`、`freezedetect` | 记录区间，不自动判合格 |
| 电平/峰值 | `volumedetect` | 均值、峰值在目标范围 |
| 响度 | `loudnorm`/`ebur128` | integrated LUFS、true peak |
| 切点 | 抽帧 + 波形 | 硬切无叠影、无爆音、无重复对白 |
| 字幕 | `caption_frame_qc.py` 抽帧 + 人工看联系表 | 报告默认 `review_required`；`media_qc.py --caption-report --require-caption-review` 才把该门计入交付；无模型自创字幕，位置不遮脸 |

机械检查只证明“文件没坏”，不证明表演、构图、混音平衡或观众接受。

## 8. 交付

- 输出先写 `*.tmp.mp4`，成功后原子改名为目标文件；失败不留半成品。
- 生成 `assembly-report.json`：输入清单、每段时长、总时长、规格、响度、峰值、检查结果、已知缺陷。
- 记录源文件哈希、EDL 版本、字体/字幕版本、混音参数；返工时可复现。
- 不把“能播放”当成“合格成片”；按 `qualified-video-acceptance.md` 完成看片与听辨后再改状态。

## 9. 与本 Skill 的衔接

- 第 8 步（Select and assemble）：读本文件，先 conform 再拼接；镜头间禁止叠化。
- 第 9 步（Build sound）：按 4.1–4.3 做电平、混音和接缝；不重复对白。
- 第 10 步（Watch, repair, rewatch）：用 `scripts/media_qc.py` 加本文件第 7 节的检查；机械结果不等于验收。
- 第 11 步（Deliver）：按第 8 节生成报告与原子输出。
- 提交前运行 `scripts/ffmpeg_conform_check.py`；BLOCK 未清零不拼接。

## 10. 非目标

- 不替作者做剪辑决策、表演判断或剧情改写。
- 不生成提示词、不代写字幕文本、不做未经授权的翻译。
- 不把云 API、账号、密钥或私有素材写进仓库或命令历史。
