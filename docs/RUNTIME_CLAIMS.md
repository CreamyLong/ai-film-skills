# 运行时断言登记

本表只登记“模型 / 插件 / 运行时**会怎样**”的断言。创作方法、镜头语法、审片标准不在此列，除非被写成硬门。

每条必须标：

- **class**：`official`（官方文档）/ `measured`（本项目可复现实测）/ `heuristic`（生产经验）/ `unverified`
- **evidence**：来源文件、commit、测试命令或样本范围
- **gate**：是否允许作为 blocker

## H3 提示词与生成

| 断言 | 位置 | class | evidence | gate |
|---|---|---|---|---|
| 六段式 Ref2VA 结构、`<Subject N>`、`<d>[Language]` | `produce-ai-video/references/h3-official-prompt-contract.md` | official | MiniMax-AI/MiniMax-H3 的 h3-prompt-writing 参考文档 | 是 |
| 单次 5–15 秒内可用 `[Shot N] At …` 切镜 | `h3-timeline-director.md` §0.1 | official | 同上，base 参考文档第 86–92 行 | 是 |
| >15 秒按连续动作拆段、正重叠 22 帧 | `h3-timeline-director.md` | official + measured | 官方分段规则；插件 README 的 overlap 说明 | 是 |
| 0 重叠不继承 latent，不能当连续性机制 | `h3-timeline-director.md` | official | 插件 README / 采样层说明 | 是 |
| turbo 4-step LoRA 配 normal/beta 会崩坏 | `h3-timeline-director.md` | measured | SC001 同镜 normal/beta 输出过曝条纹、换脸 | 是（调度器硬门） |
| 双人近景在 4 步下不稳定，8 步可用 | `h3-timeline-director.md` §0.3 | measured | EP012 shot04 同提示词对照：4 步出现漂浮红环/巨脸/身份漂移；8 步同镜 9.4 秒两人稳定同框 | 是（双人近景默认 8 步） |
| 参考图实际内容与提示词声称不符会生成漂浮物件 | `asset-scene-consistency.md` | measured | EP012 把整张正面像标成 “isolates the scar”，H3 在肩头/衣领反复生成红色环 | 是（参考图角色核对） |
| 双人同框的两句对白会被模型对调说话人 | `h3-timeline-director.md` §0.4 | measured | EP012 shot14：儿子台词由父亲口型说出，父亲台词由儿子口型说出；拆 14A/14B 后各自 pass | 是（逐句拆单人镜） |
| 带字文件做特写会持续乱码，写“背面朝上/失焦”也压不住 | `h3-timeline-director.md` §0.4 | measured | EP012 shot07 四版、shot12、shot14 均在文件封面生成红字乱码 | 是（文件不进入特写） |
| 结构问题改提示词无效，必须改镜 | `shot-risk-and-rework.md` | measured | EP012 shot07 五版：口型→多人→乱码→乱码+脸崩，最后删动作/前景才 pass；shot14 拆 14A/14B 才 pass | 是（第二次结构失败即改镜） |
| 512×896 草稿可提前发现结构问题，约快 3 倍 | `shot-risk-and-rework.md` §6 | measured | EP012 shot07 同 prompt/seed：草稿 512×896 约 6 分钟，正式 768×1344 约 18 分钟；草稿 pass 且身份/服装/构图一致 | 是（草稿只作结构门，不作验收） |
| 分段 `images` 漏挂提示词里的角色/场景会换装、换房或造人 | `h3-timeline-director.md` §8.1 | measured | EP012 同场镜头因缺角色/场景参考出现绿衣前景人、办公室代替安全屋、桌面材质变化 | 是（`timeline_reference_check.py` block） |
| 场级连续多段（22 帧重叠）可解决空间/服装/轴线连续，但每段必须挂全所有出镜角色参考 | `h3-timeline-director.md` §0.1 | measured | EP012 A/B：缺参考版 20s 连续体 review 2 major（远景造人、反打身份不符）；每段挂全 5 参考版同内容仅 1 个资产级 major（外套 Logo）+1 minor | 是（配方前置条件） |
| 单段内多 `[Shot N]`、含换场，是官方能力 | `h3-timeline-director.md` §0.1 | official | MiniMax-H3 MV 示例：同一段 `[Shot 1]` 录音棚 → `[Shot 2] At 00:01.900` 天台；每 shot 有 keyframe panel + retention + 锁定原音贯穿 | 是（需四条件，缺一拆镜） |
| 单段超过 362 帧会整段崩坏 | `h3-timeline-director.md` | measured | SC002 753 帧单段输出从首帧起为噪声 | 是（段长硬门） |
| `<d>` 可能烧录字幕 | `prompt-compilation-preflight.md` | measured | 2026-11 本项目 20 集、24 个对白镜抽检 | 否，生成后复查 |
| 负向词会召唤被否定对象 | `prompt-compilation-preflight.md` | measured | 本项目 H3 实测，信封/手机/人物被画入 | 否，提示词建议 |
| 去掉 `<d>` 改无引号写法会导致台词含糊 | `prompt-compilation-preflight.md` | measured | EP008 shot05 对照：旧写法转写为「几许钱…」，官方标签一次说对 | 是（必须用官方标签） |
| `locked` 会原样保留 TTS 错词 | `h3-timeline-director.md` | measured | EP008 locked_shot11 波形相关 0.9991，内容仍错 | 是 |

## 音频与剪辑

| 断言 | 位置 | class | evidence | gate |
|---|---|---|---|---|
| 逐镜独立生成会产生电平/底噪跳变 | `audio-continuity.md` | measured | EP019 16 镜平均电平 -14.0~-23.8 dB；切点最大 +16.6 dB | 是 |
| L-cut 可降低切点突兀 | `audio-continuity.md` | measured | EP019 重装后同场对白切点约 ±3 dB | 否，需听辨 |
| 静帧 `tone_from` 指向对白镜会重放台词 | `audio-continuity.md` | measured | EP019 判决卡与 shot13 相关 0.993 | 是 |
| concat demuxer 会在静帧/视频交界丢帧 | `ffmpeg-assembly-toolkit.md` | measured | EP009/015/016/018 成片被截短，改 concat filter 后恢复 | 是 |

## Omni 审查

| 断言 | 位置 | class | evidence | gate |
|---|---|---|---|---|
| 参考图 vs 单帧可判换脸 | `omni-review/references/model-behavior.md` | measured | 2026-11-19，`qwen3.8-omni-flash`，C04/shot09 对照 | 否，需人工确认 |
| 跨帧网格判身份不可靠 | 同上 | measured | 同一网格判“同一人”，双图对照判“不同人” | 否 |
| 单段音频易漏切点断裂，A/B 才稳定 | 同上 | measured | 同段单送 1/5，成对送 3/5 | 否 |
| 视频自带音轨可直接转写 | 同上 | measured | 5 秒 shot05 转写正确 | 否 |
| 视频 60–90 秒可一次送 | 同上 | measured | 30/60/80 秒样本，token 7.5k/15.6k/21k | 否 |

## 标记规则

- `official` 才能写成“必须/不能”；
- `measured` 只能写成“在本项目样本上观察到”，并给出范围；
- `heuristic` 一律写成建议，不能成为 blocker；
- `unverified` 不得进入自动门，提交记录里标未验证。
