# 逐镜对照与离线结构检查

## 目标与边界

对已有剧本、镜头计划和实际投送文本，先逐镜对照“原文/已锁事实 → 导演意图和状态 → 真正提交的提示词与音频任务”。本程序帮助发现部分明确声明的遗漏和冲突，不自动读取任意分镜 Markdown、不生成修正版、不理解剧情、不验证真实文件、授权、模型输入或视频，也不拦截绕过它的外部调用。不得把 `REVIEW_REQUIRED` 当成通过；结构检查结束后仍需逐项语义、资产和授权审核。

只处理当前任务及受影响的上下游，资料不齐时标明范围和未知。用户只要求文本诊断时可用本协议检查，但不得启动媒体生成、外发或付费。用户未要求修改时只报告；已授权修订时给实际替换文本，保留未经授权的剧情、镜数、台词和时长。

## 准备输入

由执行者实际读取源文件并逐镜整理 UTF-8 JSON；不能把助手的推测当原文。下例是虚构格式示意，不是生成稿：

```json
{
  "schema": "film-skills.shot-preflight/v1",
  "tracked_items": ["parcel"],
  "shots": [
    {
      "id": "S01",
      "duration_seconds": 4,
      "prompt": "Mira places the parcel on the table. Mira says: Take it.",
      "audio_route": "native",
      "dialogue": [{"speaker": "Mira", "text": "Take it."}],
      "speech_timing": {"measured_seconds": 1.2, "window_seconds": 2, "basis": "timed read", "cross_shot": false},
      "entry_state": {"parcel": "Mira"},
      "exit_state": {"parcel": "table"},
      "state_actions": {"parcel": "Mira places the parcel on the table."}
    },
    {
      "id": "S02",
      "duration_seconds": 4,
      "prompt": "Mira picks up the parcel. She walks outside.",
      "audio_route": "silent",
      "dialogue": [],
      "transition": "cut",
      "entry_state": {"parcel": "table"},
      "exit_state": {"parcel": "Mira"},
      "previous_tail_claim": {"parcel": "table"},
      "state_actions": {"parcel": "Mira picks up the parcel."}
    }
  ]
}
```

录入规则：

- `prompt` 是这一单元准备实际提交的完整视频文本，不是 BEAT 或分镜说明；每句适用原台词放入 `dialogue`，不自行丢句。`audio_route` 为 `native`、`external` 或 `silent`。原生路线逐字在视频文本匹配；外配路线把实际准备的配音任务文本写入 `audio_prompt`，逐字在其中匹配。外配任务文本或匹配结果不代表配音已生成或已授权。
- `speech_timing` 是带停顿的实际试读/录音总耗时、对应音频窗口和依据，不使用固定字数阈值；未知则省略并保持待核。声音确实跨镜时，`cross_shot` 为 true 并填实际跨镜窗口，人工核验音轨、重叠与整片时间；程序不验证后续镜是否真的有空位。
- `tracked_items` 是当前需要交接的关键对象 ID；各镜的 `entry_state` 和 `exit_state` 必须覆盖这些 ID，值为简明状态或 `null`（未知）。状态记录对象的持有人/位置及必要状态，不用左右投影代替世界位置。`state_actions` 可引用实际视频文本中导致镜内改变的原文片段；匹配只证明字符串存在，不证明行为合理或生成成功。
- 后续镜用 `transition` 标明 `continuous`、`cut` 或 `ellipsis`。当跨镜状态改变，`entry_changes` 中按对象 ID 写明有依据的交接或省略；程序不会核实解释是否真实，仍须回查来源。普通时空跳跃不要求重拍每个动作。
- 如有“上一镜尾态”声明，录入 `previous_tail_claim`；程序与上一镜的已录入 `exit_state` 对照，而不是把本镜开场当上一镜尾帧。`initial_frame` 可记录实际输入的起始参考标识；连续镜重复使用同一原始首图只提示复核，不自动认定画面错误。

## 运行与修复

```text
python scripts/shot_preflight.py --input <当前任务的本地JSON>
```

程序不联网、不更改输入，只输出状态、问题位置、修复方向、输入和视频文本的 SHA-256。`BLOCK`/`INVALID_INPUT` 退出码为 1；其余输出 `REVIEW_REQUIRED`、退出码为 2，因为剧情、资产和实际投送均未由程序验证。不要把退出码 2 当成许可提交。哈希只标识本次输入，不证明之后实际发送的内容相同。

针对问题依次处理：对白遗漏先核对是原生还是外配，补回正确实际任务；口述超时先复核计时，再提出延长、跨镜或其他授权方案；物件错位追查最早一次出入状态并补有证据的交接；上一尾态错记则从前镜修正。用户锁定项冲突时停止并呈交选项，不直接改剧情。修复后用更新后的真实提交文本重新整理并重跑，逐项核对下游；除非真实工具链强制绑定最终 payload，否则该程序的结果不能阻止绕过调用。

## 资料来源

以下公开资料于 2026-10-30 检索，仅支持相应原则，不证明本项目模型效果：

- [Google Cloud：视频生成提示词指南](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/video/video-gen-prompt-guide)：画面与声音可分别明确描述；实际语法须查目标模型。
- [Google Cloud：首尾帧生成](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/video/generate-videos-from-first-and-last-frames)：首帧与尾帧是具体模型输入能力，不能假设所有平台相同或保证一致。
- [BBC Academy：运动方向与剪辑](https://downloads.bbc.co.uk/academy/collegeofproduction/docs/crossing_the_line_movement_ts.pdf)：画面方向的变化会影响观众理解；并非禁止有意换轴或时空跳跃。
- [BBC World Service：对白朗读](https://www.bbc.co.uk/worldservice/programmes/radioplay_tips.shtml)：朗读有助于判断对白表现；本工具因此用任务具体计时，不虚构通用语速。
- [OpenTimelineIO：时间线结构](https://opentimelineio.readthedocs.io/en/latest/tutorials/otio-timeline-structure.html)：片段、空隙与转场是不同编辑元素；允许明确设计的省略和跨镜声音。
