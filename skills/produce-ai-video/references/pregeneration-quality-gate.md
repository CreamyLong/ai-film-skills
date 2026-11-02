# 批量生成前质量门

## 适用条件

在把已定稿的导演包与逐项完成并复核的提示词放大到媒体批量生产（多场次、全片）之前，或改动提示词转写规则之后，用固定语料验证当前流程确实产出优于基线的画面。门不过就停批量——批量只会把坏流程的问题按镜头数放大，并烧掉生成预算。本门不替代逐片验收：通过门后，实际片段仍走包内合格视频验收门。

本门只授权质量合格后的媒体批量执行，不授权脚本生成提示词，也不替代用户的媒体执行与费用授权。每个用例的基线与候选提示词均由 Agent 逐项理解、撰写和复核；脚本不得按机制字段循环套模板、替换变量、拼接正文或批量调用模型代写。质量门通过不能豁免 `SKILL.md` 的提示词逐项创作硬规则。

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

视频编译层的固定机制示例：`identity_anchor`（角色锚点引用）、`action_evolution`（已选动作的演进）、`camera_motion`（明确导演选定的固定或移动机位）、`audio_clause`（适用声音条款）、`micro_performance`（适用主体的可见微表演）。机制是按用例适用性启用的测试项，不要求每镜都有运动、人物表情或声音。按当前包的编译规则定名，定下后不随意增删。

加入手部或物件特写、静止镜头及多个主体状态不同的回归用例与负向断言：例如活着的法医操作死者的手，编译不得把死者写成眨眼，也不得因法医存在而要求其未入镜的面部表演。检查增强前后实际文本和最终画面；机制字段为 false 不是逐帧视觉证明。

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
| story_readability | 5 | 不读提示词也能理解本用例的动作、信息与情绪变化 |

每维使用 0–5 分：0 未兑现/严重冲突，1 大部分失效，2 部分成立但明显妨碍观看，3 基本可用，4 完整有效且仅有轻微问题，5 高质量兑现。加权总分为 `Σ(维度分/5×权重)`，满分100。无对白、静止或无切镜用例按既定意图是否兑现评分，不因缺少不需要的运动/声音扣分。替代 rubric 须在生成前另行冻结并人工复核，不修改本次已运行门的定义。

## 聚合与判定

- 每个用例至少 2 个 replicate（不同种子/不同次生成），按维度均值聚合；同种子重复不算 replicate。
- 本默认 rubric 的冻结判定线：每个非对照用例候选均分不得低于基线超过2分；development 非对照用例平均收益至少1分；任一用例任一维度的均值退步不得超过1分（0–5尺度）。holdout 非对照用例同样执行2分回归线，不参与调参。
- **negative control 是评审有效性检查**：各对照用例候选相对基线的均值差绝对值不得超过2分。单次小幅胜出不直接判偏，超过边界则门无效并复查随机波动、标签泄露或评审偏差；不声称两次重复具有统计显著性。
- 至少有 development、holdout 和 negative control 用例。每份报告记录实际两版素材文件及哈希、不同生成的标识、盲标映射的隔离保管者、看片证据和复核授权。标签在评分完成后才揭盲；证据或播放缺失则未完成，不以模型自报评分补足。
- `holdout` 用例只作终验：不得根据 holdout 结果调参、改 rubric 或改编译规则；要调只动 development，改完全部重跑。
- `case_spec` 只进评审与生成任务书，不得把评分证据或期望答案写进生产提示词——那是过拟合，不是质量。

## fail-closed

任一情况停批量并如实报告，不允许"大体通过"：

- 语料或报告字段缺失、机制声明与 trusted 语料不符；
- `preference` 与总分矛盾、replicate 数不足、种子重复；
- negative control 的均值差绝对值超过冻结的2分边界；
- development 平均收益不足1分、任何非对照用例均分退步超过2分，或任一维度均值退步超过1分；
- 缺实际素材、播放/授权证据、development/holdout/对照或最低重复次数。

门失败时回到归属层修复：规则问题回编译层，设计问题回导演层；修复后重跑整门。不得为了通过门而放宽 rubric 或换掉不利用例。

运行 `python scripts/quality_gate_check.py --input <门记录.json>` 核对本默认 rubric 的算术、重复数和阈值。输入含 `cases` 与 `reports`；cases 每项至少给 `case_id/split/negative_control`，reports 每项给 `case_id/replicate_id/generation_ids`（两次生成标识）、`candidate_label`（揭盲后 A 或 B）、`scores.A/B`（全部维度）、`evidence.A/B` 和 `preference`（A/B/tie；差值绝对值≤0.5分算tie）。脚本不生成提示词、不联网、不看片、不验授权，也不验证素材文件；结构有效仍仅返回 `REVIEW_REQUIRED`，提交前必须另核以上实片与盲评证据。
