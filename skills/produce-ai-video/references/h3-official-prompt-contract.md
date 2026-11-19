# 官方 H3 提示词合同（Ref2VA）

来源：`MiniMax-AI/MiniMax-H3` 仓库 `skills/h3-prompt-writing/references/ref-en.txt` 与 `base-en.txt`。本页是执行摘要，冲突时以官方原文为准。

## 1. `detailed_description` 必须写清六件事

每个镜头按播放顺序写：

1. **composition**：景别、机位、主体在画内的位置；
2. **subject appearance / position**：外观、服装、姿态、朝向；
3. **environment and lighting**：空间、固定陈设、光从哪来、照到什么表面；
4. **actions and state changes**：动作过程与首尾状态；
5. **camera movement**：运动类型、幅度、速度；
6. **current sound**：本镜真实发出的声音。

不能写成剧情摘要，也不能只列参考关系。生成任务通常 350–500 英文词；对白密集时优先保证台词时间轴，不机械凑字数。

## 2. 光影是环境，不是形容词

- 写清主光/辅光/轮廓光/实用光、方向、强度、色温，以及光照到的材质。
- 不写 `cinematic lighting`、`moody light` 这类空词；它们不提供方向，模型会自行发明光晕、光丝。
- 特写要写“脸上只有仪表盘冷光”“窗外路灯在右后方”，而不是“柔和的黄昏光”。

## 3. 镜头运动写类型、幅度、速度

- 类型：push in / pull out / truck left / pan right / tracking / static；
- 幅度：small / medium / large；
- 速度：slow / moderate / fast。

只写 `locked off` 不构成控制；模型仍可能横移。生成后要按实际画面验收。

## 4. 对白用官方 `<d>` 语法

```text
<Subject 1> (S1) says, <d>[Chinese] 沈国栋死亡后第三天。</d>
```

- 说话人先给 `<Subject N> (Sx)`，再写说话动词；
- 画外说话用稳定的声音描述 + `(Sx)`，并写明在画角色嘴唇闭合；
- `<d>` 内保留原语言与逐字内容，句末用 `.` `?` `!`；
- 听不清写 `[unclear]`，不猜、不改写；
- 只参考音色时，不把参考音频的原台词带进目标视频。

## 5. 不写负向词

H3 没有负向提示通道。`no truck`、`no light streaks`、`without people` 会把被否定的对象当元素生成。

改成正向物理状态：

| 不要写 | 改写成 |
|---|---|
| no light streaks | the only light is the dashboard glow from below; the glass is clean |
| no people | an empty street |
| no blur | tack sharp |
| don't move the camera | the camera is static, small amplitude, slow speed |

## 6. 参考标签

- `<Subject N>`：可复用的角色/物体；
- `<Picture N>`：具体帧或构图锚；
- `<Video N>`：编辑源、续接起点或时间结构；
- `<Audio N>`：复制或参考的音频；
- 标签一旦分配，五个段落里含义不变；
- 只为定义角色/场景/风格的图片，写进对应 `<Subject N>`，不单独占一行。

## 7. 与本地门的关系

| 门 | 检查什么 |
|---|---|
| `context_ir_check.py` / `h3_base_check.py` | 六段结构、`<d>` 语法、标签完整性 |
| `scene_plan_check.py` | 场级光源、环境图、出入状态、画外听者 |
| `dialogue_content_check.py` | 生成后的 ASR 是否真的说了这句 |
| `caption_preflight.py` | 是否写了技术规格、Speaker ID、引号台词 |

合同不保证生成正确；它只保证提交的提示词是模型能解析的官方形态。
