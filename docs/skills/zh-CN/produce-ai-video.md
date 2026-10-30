# produce-ai-video｜合格成片生产

| 状态 | 当前源码为隔离整改候选；既有安装记录与用户接受另列。 |
|---|---|
| 单独可交付 | 完整生产与验收合同；宿主工具和权限齐全时，可交付真实审核后的最终视频。 |
| 单独不能声称 | 只安装 Skill 不会自动获得模型、额度、版权、剪辑工具或合格成片。 |

[运行正文 `SKILL.md`](../../../skills/produce-ai-video/SKILL.md) · [ai-storyboard-director-v5.8.6 ZIP](https://github.com/62656456/ai-film-skills/releases/download/ai-storyboard-director-v5.8.6/produce-ai-video.zip) · [安装说明](../../INSTALLATION.md) · [兼容说明](../../COMPATIBILITY.md) · [设计总则](../../SKILL_DESIGN_SYSTEM.md)

本发布快照统一分镜5.8.6提示词合同及制作交接；历史归档保持原内容。

<!-- contract:purpose -->
## 1. 设计目的

通过导演、分镜、生成、剪辑、声音、完整回放和修复，把批准剧本或片段做成合格可观看 AI 成片。

<!-- contract:principles -->
## 2. 设计理念

- 最终可观看视频才是结果；提示词、片段、剪辑工程和 QC 报告只是中间产物。
- 保留锁定源事实，审核完整最终渲染，不用漂亮单帧代替。
- 修复观众最早失去信任的位置，并严格区分候选成片和合格成片。

<!-- contract:standalone -->
## 3. 适合单独使用的范围

当点名结果落在以下边界内时，可以只拿这一个模块使用：

完整生产与验收合同；宿主工具和权限齐全时，可交付真实审核后的最终视频。

**单独不能声称:** 只安装 Skill 不会自动获得模型、额度、版权、剪辑工具或合格成片。

<!-- contract:inputs -->
## 4. 输入

- 当前批准剧本、资产、视觉规则、决定、检查点、交付格式和合格定义。
- 付费生成、外部服务、音乐、声音、发布等重要动作的明确权限。
- 在自主生产与用户直接导演模式之间明确选择，尤其已有锁定分镜或结构时。

<!-- contract:workflow -->
## 5. 流程逻辑

1. 只有实际视频请求才进入；继承现行导演方案、分镜与批准，只补执行缺口。
2. 保留已选镜头设计，用本包编译器执行，不要求配套技能。
3. 选择生成路线，产生真实运动，完成剪辑、声音和最终文件渲染。
4. 至少完整观看两遍：一遍看故事与情绪，一遍看技术与连续性。
5. 修复阻塞问题，并以“合格成片 / 候选成片 / 未完成或待验证”诚实交付。
6. 按视觉风格第二、末尾附不编号负面提示词的现行六模块顺序保全已选摄影，专业光学名称与可见过程一同交接。
7. 每次实际视频模型提交前审核准确的提交内容、已审资产及相关剧情和跨集交接；硬条件未解决时修复或停止，再核对真实素材与受影响的接缝。
8. 记录提示词编译范围、增补、回退及素材绑定；比对本地预检哈希，并保留独立语义和关键帧审核。
9. 目标运行时接受官方 H3 Context-IR 格式时，按六段结构编译，使用语义化 Subject 标签、关系标记、镜头时间与台词标签，在提交记录中声明 prompt_format 并运行结构校验；结构通过不证明语义、素材或连续性合格。
10. 目标运行时走 H3 基础模式（t2va/i2va/fl2va/l2va）时，按官方三字段结构编译，带该模式的对齐指令、镜头时间与台词标签，在提交记录中声明 prompt_format "h3_base" 与 h3_mode 并运行结构校验；结构通过不证明语义、素材或连续性合格。
11. 面向其他提供商时，把同一批导演决定转写为该节点已核实的提示词方言——一条提示词只用一种外壳，未核实的方言保持标记 unverified——并在提交记录中登记 prompt_format 与 provider 标识。
12. 对每个生成片段与合成成片做机械质检（流、时长、分辨率、帧率、黑帧与冻结帧、音量与响度、字幕 cue 覆盖、联系表证据）；测量值只是证据，不是通过结论。
13. 按推导的 EDL、接缝核验、字幕对台词覆盖、响度与规格检查及导出清单组装交付；任一项失败都回最早责任层。
14. 每次视频模型提交的内容、依赖、审核与结果均登记到生产台账；发送前预留，未知结果先核对再决定是否重提，上游文件或审核变化时使下游失效。

<!-- contract:returns -->
## 6. 退回、重做与版本回滚

- 退回最早错误层：剧本/导演、分镜、提示词、源片段、剪辑、声音或最终渲染。
- 平台任务成功、时长正确或单帧好看都不能绕过完整回放审核。
- 用户锁定的分镜保持不变，除非明确授权修改。

<!-- contract:review -->
## 7. 审核门

- [ ] 故事、镜头、空间与资产连续性、生成质量、剪辑、声音和交付通过适用硬门。
- [ ] 真实最终文件可打开并已从头看到尾，没有用其他文件代替审核。
- [ ] 版权、费用、权限和未解决边界明确。
- [ ] 台账审核须记录明确的用户或委托权限及证据哈希；登记、哈希和网关检查只是结构检查，不能替代语义、画面、声音或连续性审核。
- [ ] 人物多视图、同空间多角度场景、适用道具及声音权利已准备；按当前范围核对连续性与提示词证据，缺证据标为待验证。

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

- [`agents/openai.yaml`](../../../skills/produce-ai-video/agents/openai.yaml)
- [`SKILL.md`](../../../skills/produce-ai-video/SKILL.md)

**引用资料**

- [`references/audio-dubbing-post.md`](../../../skills/produce-ai-video/references/audio-dubbing-post.md)
- [`references/autonomous-production-workflow.md`](../../../skills/produce-ai-video/references/autonomous-production-workflow.md)
- [`references/context-ir-format.md`](../../../skills/produce-ai-video/references/context-ir-format.md)
- [`references/h3-base-format.md`](../../../skills/produce-ai-video/references/h3-base-format.md)
- [`references/keyframe-visual-review.md`](../../../skills/produce-ai-video/references/keyframe-visual-review.md)
- [`references/pregeneration-quality-gate.md`](../../../skills/produce-ai-video/references/pregeneration-quality-gate.md)
- [`references/production-ledger.md`](../../../skills/produce-ai-video/references/production-ledger.md)
- [`references/prompt-compilation-preflight.md`](../../../skills/produce-ai-video/references/prompt-compilation-preflight.md)
- [`references/provider-shells.md`](../../../skills/produce-ai-video/references/provider-shells.md)
- [`references/qualified-video-acceptance.md`](../../../skills/produce-ai-video/references/qualified-video-acceptance.md)
- [`references/release-assembly.md`](../../../skills/produce-ai-video/references/release-assembly.md)
- [`references/segment-seam-continuity.md`](../../../skills/produce-ai-video/references/segment-seam-continuity.md)
- [`references/shot-audit-protocol.md`](../../../skills/produce-ai-video/references/shot-audit-protocol.md)
- [`references/spatial-consistency-ledger.md`](../../../skills/produce-ai-video/references/spatial-consistency-ledger.md)
- [`references/storyboard-prompt-compiler.md`](../../../skills/produce-ai-video/references/storyboard-prompt-compiler.md)
- [`references/submission-preflight.md`](../../../skills/produce-ai-video/references/submission-preflight.md)

**确定性辅助脚本**

- [`scripts/context_ir_check.py`](../../../skills/produce-ai-video/scripts/context_ir_check.py)
- [`scripts/h3_base_check.py`](../../../skills/produce-ai-video/scripts/h3_base_check.py)
- [`scripts/media_qc.py`](../../../skills/produce-ai-video/scripts/media_qc.py)
- [`scripts/production_state.py`](../../../skills/produce-ai-video/scripts/production_state.py)
- [`scripts/prompt_preflight.py`](../../../skills/produce-ai-video/scripts/prompt_preflight.py)
- [`scripts/shot_preflight.py`](../../../skills/produce-ai-video/scripts/shot_preflight.py)
- [`scripts/submission_gateway.py`](../../../skills/produce-ai-video/scripts/submission_gateway.py)

**新构建 ZIP 的分发许可文件**

新构建会将下列文件附在 ZIP 内的 Skill 目录，不修改运行源码；既有历史 Release 附件不变。

- [`LICENSE`](../../../LICENSE)
