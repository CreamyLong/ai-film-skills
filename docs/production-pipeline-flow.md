# AI 短剧生产流程图

从剧本到鉴赏家好评的单集闭环，以及跨集的资产级聚合。

## 单集流程（Mermaid）

```mermaid
flowchart TD
    A[剧本/分集大纲] --> B[资产包<br/>角色四图 + 场景图 + 道具]
    B --> C[场计划<br/>scene_plan_check]
    C --> D[逐镜提示词<br/>官方六段式 + d标签]
    D --> E{结构预检<br/>shot_contract_check<br/>timeline_reference_check}
    E -- block --> D
    E -- pass --> F[草稿渲染 512x896 8步<br/>约6分钟]
    F --> G[草稿结构审核<br/>人数/身份/构图/空间/道具]
    G -- 结构失败 --> D
    G -- pass --> H[正式渲染 768x1344 8步<br/>约18分钟/镜]
    H --> I[auto_review 逐镜<br/>--repair-queue]
    I -- block/major --> J[repair_router<br/>自动分类入队]
    J --> K{mode}
    K -- auto --> L[重渲/调增益/重组装]
    K -- authored --> M[改镜<br/>拆单人镜/删道具/换机位]
    M --> D
    L --> I
    I -- pass --> N[组装<br/>concat filter + 逐镜增益 + L-cut]
    N --> O[audio_continuity_check]
    O -- block --> N
    O --> P[整集 Omni 复审]
    P -- block/major --> J
    P -- pass/review --> Q[故事复述门<br/>story_comprehension_review]
    Q -- block/review --> R[补台词/反应镜/身份提示]
    R --> D
    Q -- pass --> S[鉴赏家终审<br/>acceptance_log.json]
    S -- fail --> J
    S -- pass --> T[合格成片]
```

## 跨集闭环（Mermaid）

```mermaid
flowchart LR
    A[19集复审报告] --> B[defect_triage<br/>按 defect+资产锚点聚合]
    B -- 同类>=3次 跨>=2集 --> C[资产级修复提案<br/>asset_repair_proposals.json]
    C --> D[人确认]
    D --> E[修资产一次<br/>重绑相关镜头]
    E --> F[repair_close 复跑审核<br/>closed/reduced/escalated]
    F -- escalated --> C
    A --> G[repair_queue 逐镜头任务]
    G --> F
    H[鉴赏家反馈] --> I[误报降权/主因升权<br/>connoisseur-feedback.md]
    I --> B
```

## 关键判断点

| 节点 | 通过条件 | 失败去向 |
|---|---|---|
| 结构预检 | 无 block | 回提示词改结构，**不烧 GPU** |
| 草稿审核 | 结构类 pass | 回提示词；细节问题放行到正式 |
| 逐镜复审 | 无 block | 自动路由，auto 直接修，authored 改镜 |
| 音频检查 | 无 blocker | 回组装调增益/改 L-cut |
| 整集复审 | 0 block | 回到对应责任层 |
| 故事复述 | confusions<3 且 clarity/appeal≥6 | 回剧本/分镜补信息 |
| 鉴赏家终审 | pass | 失败回路由，误报写回降权 |

## 硬规则（流程里必须出现）

- 结构失败只能改镜，不允许同一构图渲第三版；
- 带字道具不进特写，可读信息走后期静态图；
- 双人同框不塞交替台词，一人一镜；
- 同一场所有镜头共享同一套角色/场景参考；
- 组装用 concat filter，逐镜增益进 editlist；
- 每个 block/major 必须经 repair_close 复跑确认 closed 才算修完。
