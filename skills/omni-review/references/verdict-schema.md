# 判决与报告格式

## 1. 严重度

| 级别 | 定义 | 处理 |
|---|---|---|
| blocker | 观众直接出戏或看不懂 | 未清零不得称为成片 |
| major | 持续削弱可信度 | 本版修复或明确记录接受 |
| minor | 非焦点区小瑕疵 | 可延后，不阻断 |

同一条问题只归一层，不重复计数；修复后重跑同层。

## 2. 单条记录

```json
{
  "id": "EP019-T1-09",
  "tier": "T1",
  "severity": "blocker",
  "shot": "09",
  "timecode": "00:39.5",
  "claim": "生成角色与 C04 参考不是同一人",
  "evidence": "无眼镜、有胡须、发型与服装不符",
  "model_quote": "判断：不同。参考图佩戴细金属框眼镜，生成图完全无眼镜……",
  "repair_owner": "asset/prompt/generation/edit/sound",
  "human_status": "confirmed",
  "false_positive": false
}
```

字段要求：

- `timecode` 必须能直接定位；单帧写 `镜号 + 秒`，音频写秒。
- `claim` 一句话说清问题，不写“质量不佳”。
- `evidence` 是可见/可听的差异，不是模型评价。
- `human_status`：`pending` / `confirmed` / `false_positive`。
- `repair_owner` 只能选一个；跨层问题拆成两条。

## 3. 集级报告

```markdown
# <集> 成片审查

## 结论
- blocker: N
- major: N
- minor: N
- 当前状态: candidate / qualified（只有 blocker=0 且完整看片后才可写 qualified）

## blocker
- **EP019-T1-09** 00:39.5 周启明换脸
  - 证据: 无眼镜/有胡须/发型不符
  - 模型: "判断：不同……"
  - 修复: 资产层补 C04 参考，8 步重渲该镜

## major
...

## 误报
- 模型把人群随机变化写成空间跳变；已核对固定陈设，撤销。

## 覆盖
- T1: 5/5 对白特写
- T2: 3 张网格
- T3: 5/5 场
- T4: 3/3 切点
- T5: 2 场
- T6: 2 个主 key 镜
```

## 4. 判定顺序

1. 先看 blocker 是否都有人工确认证据。
2. 再看 major 是否有修复归属；没有归属的不能进修复队列。
3. 最后看覆盖：缺层的部分写“未审”，不能写“通过”。
4. 模型说“没问题”不等于通过；只表示该层未发现问题，仍需人工完整看片。

## 5. 禁止

- 用平均分、总分或“AI 评分”替代逐条证据。
- 把 `review_required` 直接改成 `reviewed`。
- 把模型幻觉当作缺陷去改片；先核对画面。
- 在报告里粘贴密钥、完整提示词内部路径或未授权素材。
