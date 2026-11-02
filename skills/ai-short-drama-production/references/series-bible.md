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

每集一个 JSON。叙事字段沿用本包节拍合同（`hook / want / obstacle / strategy_shift / power_turn / cost`），结尾填写 `cliffhanger` 或 `resolution`，按连续剧、单元剧或限定剧的本集作用选择，不强制每集制造悬念。字段必须是观众可观察的事实，不是"反转很强"；这些字段不替代整季开发。

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
- `entity_deltas.departs` 登记本集退场实体；后续当前时间线再使用须先通过 `entity_deltas.returns` 列出已注册且曾退场的实体。回归需要剧情与资产依据，声明本身不是批准；死亡不能仅靠 returns 复活。
- `threads.opens/closes` 管理情节线开合：关闭未开之线是 `SERIES_THREAD_CLOSE_UNOPENED`。
- `episode_no` 从 1 连续编号；跳号报 review。

## 3. 生产顺序

1. 立项：写 `series_bible` 的实体、初始状态与（如已知的）长期情节线。
2. 逐集写 `episode_outline`；每写完一集跑 `scripts/series_check.py`。
3. 大纲通过后，把 introduces 实体注册进 bible、建资产护照，该集才进入本包第 2 节的资产/镜头生产。
4. 该集生产完成并审核后，把完整 `episode_outline`（不是仅集号或摘要）追加进 `bible.episodes`，保留原初状态与集记录。已有集修订走明确改稿、影响核对和重新审核，不静默覆盖历史。
5. 人物外观的长期变化不在大纲里断言：新状态先登记为已批准的状态变体，再在镜头声明中引用（见资产合同的状态变体条款）。

## 4. 结构检查

```bash
python3 scripts/series_check.py --bible bible.json --outlines outlines/
```

全量检查提供全部大纲；增量检查只提供本轮大纲，程序会先重放 `bible.episodes` 中完整历史，再核对当前集。两处同集内容完全相同只检查一次；不一致报 `SERIES_HISTORY_CONFLICT`。增量缺失任何前序集报 `SERIES_HISTORY_INCOMPLETE`，不能以初始状态代替。记录报告的 `history_sha256`；恢复时用 `--history-sha256 <已核对值>` 钉住历史版本。该哈希不证明历史曾获批准，须另核项目审核记录。

检查项：bible 结构（实体 id 唯一、kind 合法、锁定人物有外观、线索开闭顺序）、历史重放与冲突、大纲字段与节拍完备、`entry_state` 对累积状态、实体注册/退场/显式回归、情节线按声明集数生效、`episode_no` 连续性。情节线登记的开闭集数与本集显式事件冲突时阻断；尚未开启的线不能提前关闭。

边界：通过只说明账能对平。钩子是否有效、收线是否有力、状态变化是否合理，仍是复核者的判断——`narrative_review` 恒为 `not_performed`。

## 5. 三种时间与生产交接

- **故事时间**记录事件实际发生的时段、先后与状态；**呈现顺序**记录观众在哪集哪场看到；**生产顺序**只安排资产和素材制作，不能改变前两者。
- 闪回、梦境、重播、假设画面单独标记 `temporal_context`、实际故事时间、依据与所需历史资产版本；不要把历史人物列成当前时间线的回归，也不要把历史伤势写回当前 `exit_state`。脚本尚不验证这些语义，必须逐场核对并记录待核项，不能借空状态绕过。
- 隐藏真相、角色所知、观众所知分开；人物何时获得信息有具体来源。新揭示须与此前可观察事实相容。
- 整季方案、表演及跨集改稿按入口要求先完成；改变某集退出状态时，列出相关后续集、镜头、资产、声音与素材，重跑结构检查并复核实际受影响内容。所有提示词仍逐项撰写，禁止脚本套模板。
