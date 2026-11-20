# 把“判断”从“生成”里拆出来：决策模型在 AI 视频生产链路上的五个实测用法

> 场景：20 集 AI 竖屏短剧《死者的第七年》的工业化生产线（ComfyUI + MiniMax H3 TimelineDirector）。
> 决策模型：书生-Decision-4B（SystemOne `/v1/systemone` 协议）。文中所有数字都来自本项目的真实生产日志，正负结果都写。

## 一、为什么视频流水线需要一个“只判断不生成”的模型

AI 视频生产最贵的资源不是 token，是 **GPU 时间**：8 步 H3 渲染一个 9 秒镜头约 18 分钟。流水线里却有大量决策点根本不要创造力，只要一个带置信度的判断：

- 这条审核发现该归到哪一层修复？
- 这 7 集里报的“换装”是不是同一个资产根因？
- 观众这个困惑是剧本没写，还是剪辑没给到？
- 这组镜头提示词的站位互相矛盾吗？
- 这版提示词有没有“台词+多动作竞争”的已知风险？

生成模型能做这些，但贵、慢、输出还要解析；规则关键词能做，但遇上没见过的措辞就漏。**决策模型正好是第三象限的产物**：一次请求提交一组判断题，返回概率化答案，不生成自由文本，只按输入 token 计费。我们的分诊一次约 300 输入 token——不到一分钱人民币，换 18 分钟 GPU 的避险。

## 二、协议速览（30 秒上手）

```bash
curl https://discovery-api.intern-ai.org.cn/v1/systemone \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{
    "model": "intern-decision-4b",
    "state": "<证据材料：文本，≤8K token>",
    "questions": {
      "is_urgent": {"type": "noul", "instructions": "Does this convey urgency?",
                    "criteria": {"true": "time-sensitive", "false": "no urgency"}},
      "route": {"type": "choice", "instructions": "Which team handles this?",
                "criteria": {"billing": "Payments", "technical": "Bugs"}},
      "anger": {"type": "score", "instructions": "How frustrated?",
                "criteria": ["Calm", "Frustrated", "Very angry"]}
    }
  }'
```

响应按题返回：`noul` → P(yes)；`choice` → 各选项概率 + 最终选择 + confidence；`score` → 各档概率 + 加权期望分。1~16 题/请求，选项 ≤62 个，RPM 独立 200，不支持流式。

**硬约束先记住**：纯文本、无视觉、不做生成。它只能替换“文本进、概率出”的环节。

## 三、五个实测用法（含两个负结果）

### 1. 审核发现的级联分诊 —— 级联 16/20，单独任一方都不及格

20 条人工标注的真实审核发现上：关键词规则 14/20，决策模型单独 13/20，**级联（规则优先，仅 unknown 交给模型，置信度 ≥0.5 才采纳）16/20**。被采纳的 12 次里 11 次正确（91.7%）；低置信答案全部被门挡住，不会带偏路由。

关键设计是**级联而非替代**：规则管得了的绝不过模型——快、免费、确定；模型只补 unknown。置信度是硬门：<0.5 宁可回到“换 seed 重渲”的保守路径。

### 2. 跨集缺陷的根因确认 —— 把 46 个镜头级任务压成 8 个资产级提案

多集复审里“外卖服 Logo 乱码”出现 9 次、跨 7 集。逐镜头重渲是 9×18 分钟；修一次资产是 1 次。聚合器按（缺陷类+资产锚点）分簇后，让决策模型判断“这些样本是否共享一个资产级根因”：8 个提案通过（根因置信 0.67–0.82），1 个被降级回镜头级。省钱之外更重要的是**返工粒度从镜头提升到资产**。

### 3. 故事复述门的困惑归因 —— 剧本缺口 vs 剪辑缺口

整集成片做盲测复述（不给剧本），模型列出的困惑逐条交给决策模型归因。EP012 的三条真实困惑（“黑衣男是谁”“父亲为何放线索”“署名怎么确认”）全部判 `script_gap`（置信 0.56–0.92），与人工分析一致：它们靠重渲治不好，必须回剧本/导演层补信息。这把“故事质量”问题从模糊差评变成了可路由的任务。

### 4. 渲染前连续性校对 —— 在 GPU 之前抓住轴线翻转

同一场多个镜头写清站位后（“Shen Guodong sits on the right side of the frame”），`continuity_audit` 汇总各镜头描述，问决策模型“这些镜头里该角色站位是否一致”。对照验证：修复版 EP012 pass；人为把 shot09 的父亲翻到左侧，立即报 `AXIS_CONFLICT`（agree=0.377）。前提是**先声明再校对**——提示词不写站位，它无从判起。

### 5. 提示词风险扫描 —— 台词+多动作竞争

对每镜的 `detailed_description` 评三题：台词是否伴随多个显著动作、带字道具是否成焦点、站位机位是否欠声明（P≥0.7 block）。回测：最终 pass 版 shot07 干净；有风险旧镜被标出。

### 负结果一：改镜方案选择，模型选错了

shot07 的历史案例（连败 4 版）喂给它选改镜方案，它选 reframe（0.79）；但实测赢家是删掉道具动作（第 5 版才 pass）。**它没有那五连败的记忆，不知道 reframe 压不住文件乱码**。结论：改镜顺序仍以人工策略为准，不自动化。

### 负结果二：信号会被上下文稀释

shot07 v1 的“抽屉+文件+台词”风险，在短描述下模型能抓到 P=0.90；放进完整六段式提示词后信号被稀释漏抓。所以风险扫描定位 review 级辅助，永不单独当门。

## 四、可复用的设计模式

1. **级联**：确定性规则 → 决策模型 → 保守兜底。每层只处理上层处理不了的；
2. **置信度即门**：choice 题的 confidence 直接当采纳阈值，低置信答案视为“不知道”；
3. **风险题用反向措辞**：题目统一“true=坏事”，避免极性翻转 bug（我们踩过：一道题写成正向表述，所有镜头被全量误报）；
4. **负结果写进文档**：哪个用法被否决、为什么，防止团队后人重试；
5. **成本可忽略**：分诊 ~300 输入 token/次，只按输入计费，高频调用无压力。

## 五、什么时候不要用

- 有视觉输入的需求（它看不见图/视频）；
- 确定性比对（时长校验、哈希、编号对齐）——规则比它快且准；
- 需要创造力的环节（写提示词、想改镜方案）；
- 高置信门槛也兜不住的代价（安全审批类判断别交给 4B 概率输出单独决定）。

## 六、接入代码骨架

```python
def decide(state, questions, timeout=60):
    r = requests.post(
        "https://discovery-api.intern-ai.org.cn/v1/systemone",
        headers={"Authorization": "Bearer " + load_key()},
        json={"model": "intern-decision-4b", "state": state[:6000], "questions": questions},
        timeout=timeout)
    r.raise_for_status()
    return r.json()["answers"]
```

完整实现与全部测试见 `ai-film-skills` 仓库：`skills/produce-ai-video/scripts/decision_client.py`、`repair_router.py`、`defect_triage.py`、`continuity_audit.py`、`prompt_risk_scan.py`（`--decision` 开关），以及 `tests/fixtures/decision_triage_cases.json` 标注集。

---

* measured 数据截至 2026-11-20；决策模型限流与价格以 SystemOne 控制台为准。
