# short-drama-develop｜系列开发与分集地图

| 状态 | 改编自 MIT 许可的 drama-skills 套件；仅完成结构检查与自测，无实战或用户接受证据。 |
|---|---|
| 单独可交付 | 系列级开发包，产出 项目开发/ 合同集；与剧本写作包配套使用，纯规划请求也可独立运行。 |
| 单独不能声称 | 不写场景动作与台词，不拆资产，不写提示词，不生成媒体，不签发终审结论。 |

[运行正文 `SKILL.md`](../../../skills/short-drama-develop/SKILL.md) · [安装当前源码](../../INSTALLATION.md) · [安装说明](../../INSTALLATION.md) · [兼容说明](../../COMPATIBILITY.md) · [设计总则](../../SKILL_DESIGN_SYSTEM.md)

尚无发布快照；从当前源码树安装。MIT 许可保留在包内 LICENSE。

<!-- contract:purpose -->
## 1. 设计目的

把短剧/漫剧想法、小说或笔记发展成可追溯的创作简报、故事引擎、按需导演阐述、改编映射与含逐集进出状态的完整分集地图。

<!-- contract:principles -->
## 2. 设计理念

- 先用因果、人物状态和精确交接事实建立系列故事，再谈生产合同；设定、大纲或分集地图不能替代用户点名的完整剧本。
- 区分创作者提出值与已接受事实；推定设定须标明推定并经确认后才成为既定事实。
- 题材卡、钩子模式与节奏档案是可选的校准辅助，不是强制模板，也不构成质量证明。
- 题材卡仅内部校准、不进交付物；集数与钩子位置服从创作者契约，不套固定配方。
- 前提装置把创作者已接受契约与剧中披露分开；无契约条款的能力属于事后扩权。

<!-- contract:standalone -->
## 3. 适合单独使用的范围

当点名结果落在以下边界内时，可以只拿这一个模块使用：

系列级开发包，产出 项目开发/ 合同集；与剧本写作包配套使用，纯规划请求也可独立运行。

**单独不能声称:** 不写场景动作与台词，不拆资产，不写提示词，不生成媒体，不签发终审结论。

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
- [ ] 分集地图引用可解析，每集在钩子前落地当集结果，相邻集精确交接状态。
- [ ] 改编映射保留核心人物立场、核心关系与主线，除非创作者已接受该改动。

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

- [`agents/openai.yaml`](../../../skills/short-drama-develop/agents/openai.yaml)
- [`SKILL.md`](../../../skills/short-drama-develop/SKILL.md)

**引用资料**

- [`references/adaptation-craft.md`](../../../skills/short-drama-develop/references/adaptation-craft.md)
- [`references/creative-reference-intake.md`](../../../skills/short-drama-develop/references/creative-reference-intake.md)
- [`references/director-brief-craft.md`](../../../skills/short-drama-develop/references/director-brief-craft.md)
- [`references/episode-design.md`](../../../skills/short-drama-develop/references/episode-design.md)
- [`references/genre-and-hook-playbook.md`](../../../skills/short-drama-develop/references/genre-and-hook-playbook.md)
- [`references/genre-cards.md`](../../../skills/short-drama-develop/references/genre-cards.md)
- [`references/genre-cards/亲子隐秘.md`](../../../skills/short-drama-develop/references/genre-cards/亲子隐秘.md)
- [`references/genre-cards/仙侠修真.md`](../../../skills/short-drama-develop/references/genre-cards/仙侠修真.md)
- [`references/genre-cards/动作任务.md`](../../../skills/short-drama-develop/references/genre-cards/动作任务.md)
- [`references/genre-cards/古装权谋.md`](../../../skills/short-drama-develop/references/genre-cards/古装权谋.md)
- [`references/genre-cards/复仇打脸.md`](../../../skills/short-drama-develop/references/genre-cards/复仇打脸.md)
- [`references/genre-cards/家庭关系.md`](../../../skills/short-drama-develop/references/genre-cards/家庭关系.md)
- [`references/genre-cards/悬疑规则.md`](../../../skills/short-drama-develop/references/genre-cards/悬疑规则.md)
- [`references/genre-cards/生活流.md`](../../../skills/short-drama-develop/references/genre-cards/生活流.md)
- [`references/genre-cards/破镜重圆.md`](../../../skills/short-drama-develop/references/genre-cards/破镜重圆.md)
- [`references/genre-cards/系统流.md`](../../../skills/short-drama-develop/references/genre-cards/系统流.md)
- [`references/genre-cards/职场喜剧.md`](../../../skills/short-drama-develop/references/genre-cards/职场喜剧.md)
- [`references/genre-cards/豪门婚恋.md`](../../../skills/short-drama-develop/references/genre-cards/豪门婚恋.md)
- [`references/genre-cards/身份错位.md`](../../../skills/short-drama-develop/references/genre-cards/身份错位.md)
- [`references/genre-cards/逆袭.md`](../../../skills/short-drama-develop/references/genre-cards/逆袭.md)
- [`references/genre-cards/重生穿越.md`](../../../skills/short-drama-develop/references/genre-cards/重生穿越.md)
- [`references/long-series-delivery.md`](../../../skills/short-drama-develop/references/long-series-delivery.md)
- [`references/mechanism-loop.md`](../../../skills/short-drama-develop/references/mechanism-loop.md)
- [`references/multi-episode-intake.md`](../../../skills/short-drama-develop/references/multi-episode-intake.md)
- [`references/premise-devices.md`](../../../skills/short-drama-develop/references/premise-devices.md)
- [`references/reveal-reversal-payoff.md`](../../../skills/short-drama-develop/references/reveal-reversal-payoff.md)
- [`references/serial-character-and-memory.md`](../../../skills/short-drama-develop/references/serial-character-and-memory.md)
- [`references/stage-contract.md`](../../../skills/short-drama-develop/references/stage-contract.md)
- [`references/story-craft.md`](../../../skills/short-drama-develop/references/story-craft.md)

**确定性辅助脚本**

- [`scripts/episode_intake.py`](../../../skills/short-drama-develop/scripts/episode_intake.py)
- [`scripts/selftest.py`](../../../skills/short-drama-develop/scripts/selftest.py)

**其他随包文件**

- [`assets/creative-brief.md`](../../../skills/short-drama-develop/assets/creative-brief.md)
- [`assets/story-engine.md`](../../../skills/short-drama-develop/assets/story-engine.md)
- [`LICENSE`](../../../skills/short-drama-develop/LICENSE)
- [`templates/adaptation-map.example.jsonl`](../../../skills/short-drama-develop/templates/adaptation-map.example.jsonl)
- [`templates/episode-map.jsonl`](../../../skills/short-drama-develop/templates/episode-map.jsonl)
