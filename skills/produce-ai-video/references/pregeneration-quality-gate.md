# 批量生成前质量门

## 适用条件

在把已定稿的导演包与提示词编译管道放大到批量生产（多场次、全片）之前，或改动编译层规则之后，用固定语料验证当前管道确实产出优于基线的画面。门不过就停批量——批量只会把坏管道的问题按镜头数放大，并烧掉生成预算。本门不替代逐片验收：通过门后，实际片段仍走包内合格视频验收门。

## 核心结构：fixture 语料

固定 JSON，字段齐全才有效：

```json
{
  "schema_version": "1.0",
  "corpus_id": "<语料标识>",
  "holdout_policy": {"development": "<允许调参>", "holdout": "<只作终验>"},
  "cases": [
    {
      "case_id": "<唯一>",
      "split": "development|holdout",
      "genre": "<题材>",
      "negative_control": false,
      "mechanisms": {"identity_anchor": true, "action_evolution": true, "camera_motion": false, "audio_clause": true, "micro_performance": false},
      "case_spec": "<一小段镜头/任务描述，不贴长文件>"
    }
  ]
}
```

- `mechanisms` 必须声明全部固定机制名，各值为布尔；机制集合改动即语料换代，旧结果作废。
- `negative_control: true` 的用例不得启用任何目标机制。
- 至少覆盖两种题材；每个机制至少有一个 development 用例启用它。

视频编译层的固定机制示例：`identity_anchor`（角色锚点引用）、`action_evolution`（显式动作演进）、`camera_motion`（稳定构图+慢推替代固定机位字面）、`audio_clause`（声音独立条款）、`micro_performance`（微表情时间轴）。按当前包的编译规则定名，定下后不随意增删。

## 盲评 A/B

每个用例跑两版：基线（关闭目标机制或旧规则）与候选（当前管道），随机标注为 A/B，评审者不知对应关系。评审按 rubric 逐维打分并给具体证据，报告固定字段：`case_id`、`replicate_id`、`scores.A/B`、`evidence.A/B`、`preference`。`preference` 必须与总分方向一致，矛盾即该份报告无效。

rubric 维度与权重（合计 100，按本包验收重点定）：

| 维度 | 权重 | 看什么 |
|---|---|---|
| identity_consistency | 20 | 角色面部/服装与锚点一致，无换脸 |
| motion_continuity | 15 | 真实运动，非静帧幻灯片 |
| action_legibility | 15 | 动作可读、有起止与重心变化 |
| prompt_fidelity | 15 | 画面兑现导演包与分镜决定 |
| camera_and_composition | 10 | 运镜与景别符合设计 |
| audio_quality | 10 | 台词/环境声清晰，无近静音段 |
| cut_continuity | 10 | 与前后片段的接缝状态衔接 |

## 聚合与判定

- 每个用例至少 2 个 replicate（不同种子/不同次生成），按维度均值聚合；同种子重复不算 replicate。
- 判定线：候选均分不得低于基线减回归容差；development 用例整体须有正收益。
- **negative control 是评审有效性检查**：候选在未启用任何机制的对照组上"显著胜出"，说明评审在走形式或有偏，整个门判无效，而不是判通过。
- `holdout` 用例只作终验：不得根据 holdout 结果调参、改 rubric 或改编译规则；要调只动 development，改完全部重跑。
- `case_spec` 只进评审与生成任务书，不得把评分证据或期望答案写进生产提示词——那是过拟合，不是质量。

## fail-closed

任一情况停批量并如实报告，不允许"大体通过"：

- 语料或报告字段缺失、机制声明与 trusted 语料不符；
- `preference` 与总分矛盾、replicate 数不足、种子重复；
- negative control 上候选胜出；
- development 整体无收益，或任一用例出现维度级严重回归（如 identity_consistency 腰斩）。

门失败时回到归属层修复：规则问题回编译层，设计问题回导演层；修复后重跑整门。不得为了通过门而放宽 rubric 或换掉不利用例。
