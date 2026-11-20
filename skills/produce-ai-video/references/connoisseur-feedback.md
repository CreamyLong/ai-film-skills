# 鉴赏家终审反馈格式

这是 RSI 环路的最后一环：人工终审结论写回系统，用来校准审核规则和聚合阈值。没有真实终审数据前，本文件只定义格式，不产生行为。

## 文件

项目级 `制作/acceptance_log.json`，数组，每集一条：

```json
[
  {
    "episode": "EP012",
    "verdict": "pass",
    "reviewer": "鉴赏家A",
    "date": "2026-11-20",
    "reasons": ["父子对峙张力足", "结尾车灯悬念有效"],
    "false_positives": [
      {"shot": "09", "defect": "reference_lock", "note": "伤疤在资产里本就偏淡"}
    ]
  },
  {
    "episode": "EP003",
    "verdict": "fail",
    "reviewer": "鉴赏家A",
    "date": "2026-11-20",
    "reasons": ["空间断裂无法入戏"]
  }
]
```

## 字段

| 字段 | 必需 | 说明 |
|---|---|---|
| `episode` | 是 | 集号 |
| `verdict` | 是 | `pass` / `fail` / `revise` |
| `reviewer` | 否 | 谁判的 |
| `reasons` | verdict 为 fail/revise 时必需 | 自然语言原因 |
| `false_positives` | 否 | 审核误报：shot/defect/note |

## 回灌效果（实现时遵守）

1. 同一 `(shot, defect)` 被标误报 ≥2 次 → `repair_router` 对该组合降权，不再自动重渲；
2. 同一 `defect` 被多位鉴赏家指为 fail 主因 ≥2 次 → 提升其聚合优先级；
3. `pass` 集的所有未处理 minor 不再进修复队列；
4. 反馈只改路由与阈值，**不自动改提示词、不自动生成资产**。
