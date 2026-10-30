# 系列圣经与分集大纲

单片之外的长剧/连续剧需要两个产物：**分集大纲**（每集一个 `episode_outline`）和**跨集注册表**（全剧一个 `series_bible`）。两者都是控制合同：结构通过只说明账能对平，不说明剧情好坏。

## 1. `series_bible` 注册表

每部剧一个 JSON。实体只允许三类：`character`、`location`、`prop`。

```json
{
  "series_id": "s01",
  "title": "示例剧",
  "entities": [
    {"id": "C01", "kind": "character", "name": "林岚", "appearance": "齐耳短发，灰西装，左眉疤",
     "locked": true, "asset_ref": "C01"},
    {"id": "S01", "kind": "location", "name": "写字楼办公室"},
    {"id": "P01", "kind": "prop", "name": "银戒指"}
  ],
  "threads": [{"id": "T1", "opened_in": 1, "closed_in": null, "summary": "戒指失踪之谜"}],
  "initial_state": [{"entity": "C01", "key": "status", "value": "healthy"}],
  "episodes": []
}
```

规则：

- `locked: true` 的人物外观一经登记不可改写；中途换状态（受伤、变老、换装）走资产护照的状态变体登记，不在大纲里用文字断言覆盖。
- `threads` 记录全剧情节线：`opened_in` 必填，`closed_in` 为 null 表示仍开放；收线集数不得早于开线集数。
- `initial_state` 是第一集之前的已知世界状态，格式与状态项一致。
- `episodes` 是已生产集的累积记录（见第 4 节回写）。

## 2. `episode_outline` 分集大纲

每集一个 JSON。叙事字段沿用本包节拍合同（`hook / want / obstacle / strategy_shift / power_turn / cost / cliffhanger`），必须是观众可观察的事实，不是"反转很强"。

```json
{
  "episode_no": 2,
  "title": "第二个戒指",
  "premise": "林岚追查戒指来源",
  "hook": "证物室里的戒指不见了",
  "want": "林岚要找回戒指",
  "obstacle": "看守否认有人进出",
  "strategy_shift": "林岚改走关系线",
  "power_turn": "看守说漏了夜班表",
  "cost": "林岚暴露了线人",
  "cliffhanger": "同款戒指出现在别人手上",
  "entry_state": [{"entity": "C01", "key": "status", "value": "injured"}],
  "exit_state": [{"entity": "C01", "key": "status", "value": "injured"},
                 {"entity": "P01", "key": "location", "value": "警局证物室"}],
  "entities_used": ["C01", "S01", "P01"],
  "entity_deltas": {"introduces": [{"id": "C09", "kind": "character", "name": "看守"}],
                    "departs": []},
  "threads": {"opens": [{"id": "T3", "summary": "夜班表造假"}], "closes": []}
}
```

规则：

- `entry_state` 是本集开场对世界状态的断言：逐项与上一集累积状态核对，不符即 `SERIES_ENTRY_STATE_MISMATCH`——改大纲，或把"戏外发生的变化"补进上一集 `exit_state`，不接受两边各写各的。
- `exit_state` 是本集结束后的新事实，进入累积状态，被下一集核对。
- `entity_deltas.introduces` 登记本集新登场实体；登场后必须先注册进 bible 并建资产护照，才允许该集投产（结构检查报 review 级提醒）。
- `entity_deltas.departs` 登记本集退场实体；退场后任何一集再使用即 `SERIES_DEPARTED_USED`。
- `threads.opens/closes` 管理情节线开合：关闭未开之线是 `SERIES_THREAD_CLOSE_UNOPENED`。
- `episode_no` 从 1 连续编号；跳号报 review。

## 3. 生产顺序

1. 立项：写 `series_bible` 的实体、初始状态与（如已知的）长期情节线。
2. 逐集写 `episode_outline`；每写完一集跑 `scripts/series_check.py`。
3. 大纲通过后，把 introduces 实体注册进 bible、建资产护照，该集才进入本包第 2 节的资产/镜头生产。
4. 该集生产完成后，把集记录追加进 `bible.episodes`，实体状态与情节线归并进 bible——世界只增不改。
5. 人物外观的长期变化不在大纲里断言：新状态先登记为已批准的状态变体，再在镜头声明中引用（见资产合同的状态变体条款）。

## 4. 结构检查

```bash
python3 scripts/series_check.py --bible bible.json --outlines outlines/
```

检查项：bible 结构（实体 id 唯一、kind 合法、锁定人物有外观、线索开闭顺序）、大纲字段与节拍完备、`entry_state` 对累积状态、实体注册/退场使用、情节线开合、`episode_no` 连续性。

边界：通过只说明账能对平。钩子是否有效、收线是否有力、状态变化是否合理，仍是复核者的判断——`narrative_review` 恒为 `not_performed`。
