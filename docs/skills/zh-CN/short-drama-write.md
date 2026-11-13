# short-drama-write｜单集剧本写作

| 状态 | 改编自 MIT 许可的 drama-skills 套件；仅完成结构检查与自测，无实战或用户接受证据。 |
|---|---|
| 单独可交付 | 单集剧本写作包，自带确定性索引与时长估算脚本；有开发包已接受产物时读取，没有时也可凭大纲直接写。 |
| 单独不能声称 | 不拆资产，不写分镜或媒体提示词，不生成媒体，不设定项目节奏档案，不签发终审结论。 |

[运行正文 `SKILL.md`](../../../skills/short-drama-write/SKILL.md) · [安装当前源码](../../INSTALLATION.md) · [安装说明](../../INSTALLATION.md) · [兼容说明](../../COMPATIBILITY.md) · [设计总则](../../SKILL_DESIGN_SYSTEM.md)

尚无发布快照；从当前源码树安装。MIT 许可保留在包内 LICENSE。

<!-- contract:purpose -->
## 1. 设计目的

写或修订可拍摄的中文短剧/漫剧单集 Markdown 剧本，支持逐集或整季批量推进，保留作者原文并规范化生产标签。

<!-- contract:principles -->
## 2. 设计理念

- 先用因果、人物状态和精确交接事实建立系列故事，再谈生产合同；设定、大纲或分集地图不能替代用户点名的完整剧本。
- 区分创作者提出值与已接受事实；推定设定须标明推定并经确认后才成为既定事实。
- 题材卡、钩子模式与节奏档案是可选的校准辅助，不是强制模板，也不构成质量证明。
- 每场必须改变信息、权力、关系、情绪、物理状态或风险；无变化的场删掉或合并。
- 对白承载意图与潜台词而非解释；创作者原文保留，不按风格规则删减。

<!-- contract:standalone -->
## 3. 适合单独使用的范围

当点名结果落在以下边界内时，可以只拿这一个模块使用：

单集剧本写作包，自带确定性索引与时长估算脚本；有开发包已接受产物时读取，没有时也可凭大纲直接写。

**单独不能声称:** 不拆资产，不写分镜或媒体提示词，不生成媒体，不设定项目节奏档案，不签发终审结论。

<!-- contract:inputs -->
## 4. 输入

- 一句话设定、题材、受众、世界/时代、核心看点、视觉形态、集数、语言，或已有笔记/小说/材料，以及点名的交付物。
- 已接受的创作决定原样传下游；缺失值保持 pending，推定值保持标注。
- 多集长材料经精确字节索引接入，不整稿塞入上下文。

<!-- contract:workflow -->
## 5. 流程逻辑

1. 先锁定创作者契约；方向未定时探索机制不同的候选，建立故事引擎，再把全剧脉络落成分集地图，然后才写场景。
2. 每集依据分集地图记录与上一集退出状态写作；每集落盘为独立剧本文件，分集地图是完成真相。
3. 有工具处做结构与连续性机械核对；叙事质量与用户接受仍是独立证据状态。

<!-- contract:returns -->
## 6. 退回、重做与版本回滚

- 因果、人物知识或集间交接失败时，先退回最早断裂的地图记录或场景，不先润色文字。
- 分集地图与已写剧集冲突时，要么显式修订地图，要么上报创作者；不静默改写剧集去迁就。

<!-- contract:review -->
## 7. 审核门

- [ ] 每集在集尾钩子前先产出当集戏剧结果，相邻集精确交接进出状态。
- [ ] 揭示、反转与回报可追溯到已建立事实；信息释放与可见载体支持的范围一致。
- [ ] 已接受节奏档案只做算术核对；缺失或未接受档案如实停用对应检查。
- [ ] 退出状态交接六项事实：谁在哪里做什么、谁知道什么、关键持物、关系/权力变化与不可撤回动作。
- [ ] 第一拍独立成立为钩子；已接受节奏档案只做算术核对，不当节拍模板强制。

<!-- contract:pass -->
## 8. 过关标准与状态

- 点名范围已落盘：规划内每集都有独立剧本文件，或交付节选被明确标注为节选。
- 续写从磁盘状态恢复，不重置集号与已接受决定。

> 下方“通过”只表示本模块规定的审核门已通过；结构有效、真实任务证据和用户接受必须分开记录。

<!-- contract:outputs -->
## 9. 输出

- 项目开发/ 下的创作简报、故事引擎、分集地图、按需导演阐述、改编映射与 project.json 节奏/语速配置。
- 剧集/<EP>/剧本.md 单集 Markdown 剧本，含场景标题、对白与生产标签。

<!-- contract:boundaries -->
## 10. 边界、依赖与权限

- 本组包不生成图像、视频、音频或提示词，不做资产拆分、分镜或终审；下游环节消费已写产物。
- 本组包改编自 MIT 许可的 drama-skills 套件；上游署名保留在各包 LICENSE 文件中。

<!-- contract:agents -->
## 11. 跨 Agent 使用

- 标准包是完整 Skill 文件夹，不是只复制一段提示词。
- `agents/openai.yaml` 只是 Codex 的可选界面元数据，不是其他宿主的运行依赖。
- 任何能读取完整文件夹的宿主均可做文本工作；自带 Python 脚本需要 3.9+，是可选辅助而非创作裁判。
- Agent 能阅读指令不等于原生发现或原生执行；提示词回退不能写成原生兼容。

<!-- contract:sources -->
## 12. 原始文件与引用

**运行正文与元数据**

- [`agents/openai.yaml`](../../../skills/short-drama-write/agents/openai.yaml)
- [`SKILL.md`](../../../skills/short-drama-write/SKILL.md)

**引用资料**

- [`references/dialogue-craft.md`](../../../skills/short-drama-write/references/dialogue-craft.md)
- [`references/production-format-dialect.md`](../../../skills/short-drama-write/references/production-format-dialect.md)
- [`references/scene-handoff-capsule.md`](../../../skills/short-drama-write/references/scene-handoff-capsule.md)
- [`references/scene-sound-dramaturgy.md`](../../../skills/short-drama-write/references/scene-sound-dramaturgy.md)
- [`references/screenplay-format.md`](../../../skills/short-drama-write/references/screenplay-format.md)
- [`references/script-craft.md`](../../../skills/short-drama-write/references/script-craft.md)
- [`references/stage-contract.md`](../../../skills/short-drama-write/references/stage-contract.md)
- [`references/substitutable-realization.md`](../../../skills/short-drama-write/references/substitutable-realization.md)

**确定性辅助脚本**

- [`scripts/duration_estimate.py`](../../../skills/short-drama-write/scripts/duration_estimate.py)
- [`scripts/screenplay_index.py`](../../../skills/short-drama-write/scripts/screenplay_index.py)
- [`scripts/selftest.py`](../../../skills/short-drama-write/scripts/selftest.py)

**其他随包文件**

- [`assets/screenplay.md`](../../../skills/short-drama-write/assets/screenplay.md)
- [`LICENSE`](../../../skills/short-drama-write/LICENSE)
