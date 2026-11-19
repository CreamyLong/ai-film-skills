# Omni 成片审判员

| 状态 | 新增源码包；仅完成结构检查和单集模型调用。尚无全剧验收证据。 |
|---|---|
| 单独可交付 | 一份证据包和按严重度排序的审查报告；不生成、不修复、不重渲媒体。 |
| 单独不能声称 | 不能证明审美、表演、剧本因果、平台合规或用户接受；模型结论必须由人核对所指帧或秒。 |

[运行正文 `SKILL.md`](../../../skills/omni-review/SKILL.md) · [安装当前源码](../../INSTALLATION.md) · [安装说明](../../INSTALLATION.md) · [兼容说明](../../COMPATIBILITY.md) · [设计总则](../../SKILL_DESIGN_SYSTEM.md)

尚无发布快照；从当前源码树安装。

<!-- contract:purpose -->
## 1. 设计目的

用多模态审查模型判断已生成的 AI 短剧成片：角色身份、烧录字幕、空间连续性、切点声音、伪影与序列清晰度，并给出帧级或秒级证据。

<!-- contract:principles -->
## 2. 设计理念

- 最终可观看视频才是结果；提示词、片段、剪辑工程和 QC 报告只是中间产物。
- 保留锁定源事实，审核完整最终渲染，不用漂亮单帧代替。
- 修复观众最早失去信任的位置，并严格区分候选成片和合格成片。

<!-- contract:standalone -->
## 3. 适合单独使用的范围

当点名结果落在以下边界内时，可以只拿这一个模块使用：

一份证据包和按严重度排序的审查报告；不生成、不修复、不重渲媒体。

**单独不能声称:** 不能证明审美、表演、剧本因果、平台合规或用户接受；模型结论必须由人核对所指帧或秒。

<!-- contract:inputs -->
## 4. 输入

- 当前批准剧本、资产、视觉规则、决定、检查点、交付格式和合格定义。
- 付费生成、外部服务、音乐、声音、发布等重要动作的明确权限。
- 在自主生产与用户直接导演模式之间明确选择，尤其已有锁定分镜或结构时。

<!-- contract:workflow -->
## 5. 流程逻辑

1. 只有实际视频任务才进入；继承批准决定，核费用/权利/改稿范围、可剪覆盖、表演选条、锁画、声音交接、真实色彩管理与目标母版，只加载适用合同。
2. 保留已选镜头设计，用本包编译器执行，不要求配套技能。
3. 选择生成路线，产生真实运动，完成剪辑、声音和最终文件渲染。
4. 至少完整观看两遍：一遍看故事与情绪，一遍看技术与连续性。
5. 修复阻塞问题，并以“合格成片 / 候选成片 / 未完成或待验证”诚实交付。
6. 调用模型前先从剪辑表、提示词和成片生成证据：每场网格、参考图对单帧的身份对、切点音频对。
7. 先跑低成本层，音频成对送；模型输出保持 review_required，直到人工确认所指证据。

<!-- contract:returns -->
## 6. 退回、重做与版本回滚

- 退回最早错误层：剧本/导演、分镜、提示词、源片段、剪辑、声音或最终渲染。
- 平台任务成功、时长正确或单帧好看都不能绕过完整回放审核。
- 用户锁定的分镜保持不变，除非明确授权修改。

<!-- contract:review -->
## 7. 审核门

- [ ] 核适用的故事、镜头、资产、剪辑、声音与交付门。必需检测失败或缺测量阻断交付；生成前100分rubric冻结回归/对照阈值。结构检查不证明完整播放、权利或用户接受。
- [ ] 真实最终文件可打开并已从头看到尾，没有用其他文件代替审核。
- [ ] 版权、费用、权限和未解决边界明确。
- [ ] 每条问题都带镜号或时间码、可见/可听差异和唯一修复归属；无证据的结论记为误报。
- [ ] blocker 大于零时成片只能算候选；模型没报问题不等于通过。

<!-- contract:pass -->
## 8. 过关标准与状态

- 只有完整观看并通过全部适用硬门的渲染文件，才能叫合格成片。
- 即使文件和工程存在，缺关键审核门也只能是候选或未完成。

> 下方“通过”只表示本模块规定的审核门已通过；结构有效、真实任务证据和用户接受必须分开记录。

<!-- contract:outputs -->
## 9. 输出

- 用户点名的真实可播放成片、单镜或视频测试，附已验证范围与状态。
- 必要的中间产物，以及审核、修复、权利和剩余边界的简明记录。

<!-- contract:boundaries -->
## 10. 边界、依赖与权限

- 禁止编写或运行批量生成提示词的脚本，不得循环套模板、替换变量、拼接正文或批量调用模型代写。完整提示词须逐项撰写复核，脚本只可校验或原样保存已完成正文；编译、事后润色和多条请求均不构成例外。
- 安装本方法不会自动获得视频模型、付费额度、音乐权、声音权或发布权。
- 不把分镜、提示词、生成片段、剪辑时间线或未审渲染冒充成片。
- 创意思路、工作流测试或查看文字阶段成果不授权生成；明确的单镜视频测试只执行点名范围。

<!-- contract:agents -->
## 11. 跨 Agent 使用

- 标准包是完整 Skill 文件夹，不是只复制一段提示词。
- `agents/openai.yaml` 只是 Codex 的可选界面元数据，不是其他宿主的运行依赖。
- 真实生产需要媒体生成、剪辑、声音、文件能力、足够权限或预算以及完整回放；纯文本宿主只能读方法，不能声称成片。
- Agent 能阅读指令不等于原生发现或原生执行；提示词回退不能写成原生兼容。

<!-- contract:sources -->
## 12. 原始文件与引用

**运行正文与元数据**

- [`agents/openai.yaml`](../../../skills/omni-review/agents/openai.yaml)
- [`SKILL.md`](../../../skills/omni-review/SKILL.md)

**引用资料**

- [`references/model-behavior.md`](../../../skills/omni-review/references/model-behavior.md)
- [`references/qwen-mm-plugins.md`](../../../skills/omni-review/references/qwen-mm-plugins.md)
- [`references/review-tiers.md`](../../../skills/omni-review/references/review-tiers.md)
- [`references/seam-review.md`](../../../skills/omni-review/references/seam-review.md)
- [`references/verdict-schema.md`](../../../skills/omni-review/references/verdict-schema.md)

**确定性辅助脚本**

- [`scripts/episode_audit.py`](../../../skills/omni-review/scripts/episode_audit.py)
- [`scripts/omni_review.py`](../../../skills/omni-review/scripts/omni_review.py)
- [`scripts/seam_review.py`](../../../skills/omni-review/scripts/seam_review.py)

**其他随包文件**

- [`LICENSE`](../../../skills/omni-review/LICENSE)
