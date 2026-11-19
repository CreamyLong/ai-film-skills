# 渲染后自动多模态审核门

每个镜头或场级片段渲染完成后，自动压缩并送一次多模态审核，拿到结构化判决后再决定是否进入组装。目标是让“换脸、换房间、切点断裂、伪影、台词含糊”在进入剪辑前暴露，而不是等成片才发现。

## 1. 触发点

| 时机 | 送什么 | 失败处理 |
|---|---|---|
| 单镜渲染完成 | 该镜原片（压缩到 384p） | `block` 停在当前镜，不进同一场 |
| 场级多镜片段完成 | 整段场片（≤90 秒） | `block` 停在该场，不进组装 |
| 重渲完成 | 同一镜/场的新文件 | 重跑审核，保留上一版报告对照 |

不审核：没有配置密钥、没有可用多模态端点、或用户明确只做技术测试。此时报告必须写“未审”，不能写通过。

## 2. 判决协议

```json
{
  "status": "pass | review | block",
  "issues": [
    {"time": "00:03.2", "severity": "block", "claim": "换脸", "evidence": "眼镜/胡须/发色不符"}
  ]
}
```

- `block`：观众会立刻出戏，停止组装；
- `review`：疑似问题或模型回答不可解析，人工看；
- `pass`：只表示本次调用未发现问题，不等于人工验收。

退出码：`0 pass`、`1 block`、`2 review`、`3 error`。流水线必须把非 0 当作未通过。

## 3. 审核提示词

固定一项任务，要求 JSON，禁止开放式“评价一下”：

> Review this generated drama clip. Check, with timestamps: identity and wardrobe continuity across cuts; space and light continuity; action/eyeline at each cut; artifacts (extra fingers, ghosting, melting textures, gibberish on-screen text); whether spoken dialogue is clear and matches the visible speaker. Return JSON only …

`block` 只给“观众会立刻发现”的缺陷，避免模型把轻微差异升级成阻断。

## 4. 成本与延迟

- 1080p 以下、≤90 秒的片段压缩后约 1–3 MB；
- 单次约 2–3 千输入 token、5–8 千输出 token，延迟 60–120 秒；
- 每场一次，单集 5–8 次调用；比逐镜送更省。

## 5. 运行

```bash
python3 scripts/auto_review.py --video video/scenes/shotSC001.mp4
```

- 报告写到同目录 `<name>_omni_review.json`；
- 只从 `OMNI_API_KEY` / `DASHSCOPE_API_KEY` 读密钥；
- 不把密钥写进命令、仓库或报告。

## 6. 硬规则

- 没有审核报告或报告是 `review`/`error`，不得进入组装；
- 模型说 `pass` 不能替代人工完整看片；
- `block` 的修复必须回到最早责任层（资产/提示词/生成/剪辑/声音），不能靠后期遮；
- 重渲后必须重跑同一提示词，保留前后报告，证明问题消失；
- 模型误报要记录 `false_positive`，不能默默忽略。

## 7. 与现有门的关系

| 门 | 负责 |
|---|---|
| `caption_preflight` | 提交前字幕/规格风险 |
| `caption_frame_qc` | 本地六帧字幕抽检 |
| `dialogue_content_check` | ASR 与台词文本比对 |
| `auto_review.py` | 渲染后身份/空间/切镜/伪影/台词的综合分诊 |
| 独立接缝审查流程 | 两个已剪片段之间的接缝 |
| 人工完整看片 | 最终接受 |
