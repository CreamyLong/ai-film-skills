# 提示词编译、增强与素材绑定

本合同的“编译”是 Agent 依据已定镜头逐项撰写和复核完整正文，不授权脚本生成提示词。禁止编写或运行批量生成提示词的脚本；不得循环套模板、替换变量、拼接片段或批量调用模型代写。脚本只可校验、原样保存或封装已经逐项完成并复核的完整正文，不得补写或改写内容。发现违规产物须停交付、停提交，回源材料逐项重写；先批量生成再润色不能替代此要求。

## 适用范围

本流程借鉴 OpenH3-IR 的分离编译、限制增补、绑定引用、校验和回退留痕思路，以本包独立实现；不安装或调用该项目，也不声称等价于 MiniMax 官方 Context-IR。对实际视频生产的每个提交单元和重试，先完成 `submission-preflight.md` 与 `shot-audit-protocol.md`，再用本协议检查实际编译结果。纯文字咨询不因此启动生成、上传或付费。

增强是可选的转换，不是“细节越多越好”。以剧本、已批准导演包和用户锁定项为上限：对每个出场主体分别记录身份、是否活着、可见部位、当前动作和画面责任；记录景别、焦点、镜头、台词、声音及首尾状态。静止、无配乐、无对白和固定摄影机都可有效。只补执行需要且有依据的内容；对新增人物、事件、动作、表演、配乐、对白、画内文字或机位变化，标明出处和授权，冲突或未知则返修或待核。

特别注意“操作死者手部”：法医的手可以有操作动作，不代表法医的脸可见；死者的状态和手部焦点不能被另一位活人的表演模板覆盖。必须直接检查实际编译后的文本及其参考图片，不以标签齐全证明语义正确。

## H3 实测失败模式

以下问题在 20 集短剧生产里反复出现，编译时必须主动规避：

- **可读文字不要交给 H3**：证件、标签、登记簿、小票、屏幕、车牌、照片正反面一律用静帧或后期文字板。模型会生成伪字，步数越高反而越容易把伪字写“清楚”。
- **手持照片必须指定朝向**：写“照片面朝下 / 背对镜头 / 只看到空白背面”，否则模型会自创一张倾斜、换人、穿西装的肖像，并与已锁定的道具图冲突。
- **取景写死头肩**：对白和反应镜写 `Tight close-up, chin to hairline; only the collar is visible at the bottom edge`；只写“medium close-up”会切头或只拍躯干。景别句必须与画面内容一致：删掉会把别的人物或交通工具拉进画面的叙述（如 `stops his e-bike`、`sees X waiting`），否则模型会用全景交代这些信息，直接破坏单人紧景。
- **负向道具/人物提及会“召唤”它们**：不要写 `no envelope`、`no phone`、`hands out of frame`、`the other character is off-camera` 这类排除句。H3 会把被否定的物件当画面元素生成，实测把信封、手机、另一角色都画了进来。改用纯正向限定：只描述画面里确实存在的东西，把景别收到 `chin to hairline`，不提该道具/人物。
- **制服与屏幕会被反向提示召唤**：写 `badge, shoulder boards outside frame` 会把便装角色画成警服；写“打开档案系统/看显示器”会把可读伪 UI、窗口边框甚至任务栏画进画面。便装角色只正向写服装本身（`dark navy zip jacket over a dark shirt`），办公室戏尽量不让屏幕入画，信息交给静帧插入。
- **负向“不笑”无效**：模型会忽略 `does not smile`。改用正向状态：`mouth tense, jaw set, eyes wide, afraid`，并检查实际帧。
- **`<d>[中文] …</d>` 会提高烧录字幕概率**：实测同一镜头改用 `says: "台词"`（去标签、保留引号）仍能正常生成对白音频，但不再出现烧录字幕。需要原生对白且不接受字幕时，优先用引号直写，不写 `<d>` 标签；若模型版本必须标签，则按随机故障重跑或改用静帧/OS。
- **烧录字幕是随机故障**：H3 会把台词烧成中英双语字幕，位置在画面下三分之一；与台词长短、道具、景别没有稳定相关，同一提示词换 seed 重跑可能消失。出现即整镜重跑，不能用裁剪或涂抹“修”，除非字幕稳定落在可安全裁掉的衣料区。字幕里还会出现英文错译和拼写错误（如 `ins hand`），不能当成片交付。提示词里的技术规格和制作标签也会被烧成文字：实测 `vertical 9:16, 24fps` 被写成画面底部的白色横幅，`Speaker ID: Qiu Jianmin = (S1)` 被写成 `Speaker ID: Jianmin ...` 的字幕条；景别和画幅由采样器参数决定，正文只写可见内容，不写 `9:16`、`24fps`、分辨率等规格。
- **提交前硬门**：对正向提示词运行 `scripts/caption_preflight.py`。出现 `subtitle/caption/watermark`、`9:16`、`24fps`、`Speaker ID` 或尺寸规格即阻断；静默/TTS 路线出现引号中文台词也阻断；原生对白的引号台词标 review，生成后必须抽帧检查。不要用“在提示词里写无字幕”来防字幕，这本身就是在点名字幕。
- **生成后硬门**：运行 `scripts/caption_frame_qc.py` 生成三帧联系表和报告；报告默认 `review_required`，人工看过后才能改成 `reviewed`。交付 QC 用 `media_qc.py --caption-report <报告> --require-caption-review`；没有报告时该门阻断。
- **背对、手部、道具特写用 8 步**：4 步会出现后脑黑斑、发际碎裂、手指粘连、衣料网格；8 步显著改善，但更慢。
- **同一角色轮换音色参考会漂移**：H3 把每条 `reference` 音频都当作音色锚点；同一说话人在不同镜头引用不同样音，会得到年龄感、厚薄、口音都不一致的“同一个人”。每个角色全片只锁一条参考，情绪写进台词与演绎指令；年轻版/电话版按独立身份锁定。
- **参考图不是越多越好**：每张参考图都参与采样；3–4 张加 `ref_image_size=max` 会明显变慢。只给当前段真正需要的身份、场景、道具。
- **屏幕与反光面**：显示器、手机、车窗容易产生摩尔纹和伪 UI。让屏幕背对镜头、只留冷光，或直接切静帧。
- **同一条连续动作才用多段**：真正的换机位/换场分别生成；不要用 0 重叠把独立镜头拼进一次执行，接缝会在表演、光位与方向上同时断开。
- **反物理一票否决**：道具尺度和人体比例、手与物体的接触、手指关节、车轮/铰链/镜架结构、悬空与穿模、同一个人出现两次、反射多出物体、阴影方向矛盾，任一项出现就必须重做关键帧或重跑 shot；信息型道具直接改静帧。不能把反物理镜头留给后期或“观众看不出来”。

## 提交记录

由执行者从当前源材料、资产清单、审批记录和**将要提交的实际模型请求**整理 JSON。下例路径和哈希是占位符，不能用于提交：

```json
{
  "schema": "film-skills.prompt-preflight/v1",
  "model": "verified-model-and-mode",
  "parameters": {"frames": 90, "fps": 24},
  "prompt": "<Picture 1> The examiner turns the deceased man's palm. Residue is visible on the fingertips.",
  "compiler": {
    "name": "local-compiler",
    "version": "v1",
    "status": "completed",
    "scope": "restrained",
    "source_prompt": "Examine the deceased man's hand.",
    "fallback_reason": null,
    "additions": []
  },
  "locks": {
    "required": ["turns the deceased man's palm", "Residue is visible"],
    "forbidden": ["The deceased man blinks", "the named facial detail fills the frame"]
  },
  "asset_inventory": {
    "coverage": "complete",
    "assets": [
      {"id": "victim", "kind": "character", "status": "approved", "version": "v1", "evidence": "victim-review-record"},
      {"id": "examiner", "kind": "character", "status": "approved", "version": "v1", "evidence": "examiner-review-record"}
    ]
  },
  "binding": {
    "scheme": "h3_explicit",
    "max_by_kind": {"image": 9},
    "capacity_evidence": "specific verified model, mode and runtime"
  },
  "attachments": [
    {
      "kind": "image",
      "label": "<Picture 1>",
      "role": "opening_frame",
      "path": "/absolute/path/to/approved-keyframe.png",
      "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
      "review": {
        "status": "approved",
        "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
        "evidence": "keyframe-review-record"
      }
    }
  ]
}
```

- `model`、`parameters`、`prompt` 和附件是该次实际请求，不是未来计划；不要把 API 密钥、令牌或其他秘密写进记录。
- `compiler.status` 为 `completed`、`fallback`、`unverified` 或 `not_used`；`scope` 为 `restrained`、`balanced`、`bold`、`extreme`、`not_applicable` 或 `unverified`，只记录实际值，不因选了克制档就宣称没有虚构内容。`not_used` 时 `source_prompt` 必须与实际文本相同；其他状态填写真实增强前文本。回退需记录 `fallback_reason`，不能因格式有效就自动放行。
- `additions` 逐条记录编译中实际新加且需核验的内容，例如 `{"kind":"music","text":"A song begins.","authorization":"unverified","evidence":null}`；`text` 必须是实际提示词中的完整片段，`authorization` 为 `authorized`、`unverified` 或 `prohibited`。已授权也要填写可追溯依据。类型可用 `dialogue`、`music`、`on_screen_text`、`performance`、`action`、`camera`、`character`、`prop`、`environment` 或 `other`。空数组不证明没有遗漏，仍需比较源和最终文本。
- `locks.required`、`locks.forbidden` 只匹配**大小写敏感的准确字符串**，不是语义理解。使用完整的实际冲突措辞，不要把裸词 `blink` 当成所有主体都不得眨眼；否定句、同义表达、引用和跨句主体都需人工或模型语义复核。锁定台词及外部配音任务仍用[逐镜结构检查](shot-audit-protocol.md)按实际声音路线逐句对照。
- `asset_inventory.coverage` 为 `complete`、`incomplete` 或 `unverified`；先从剧本、分镜与实际提示词分别清点匿名人物、场景、道具和声音，再逐项记录。`assets` 的类型为 `character`、`scene`、`prop`、`voice` 或 `other`，状态为 `approved`、`missing`、`unverified` 或 `rejected`；批准必须有版本及可追溯证据。空清单或 `complete` 只是录入声明，不证明人物提取完整或资产真实合格。
- `binding.scheme` 仅在真实运行节点采用逐文件 `<Picture N>`、`<Video N>`、`<Audio N>` 且附件顺序已知时填 `h3_explicit`，否则填 `opaque` 并人工核对模型适配器。附件按该运行时每种媒体的实际编号顺序填写；不得假定首尾帧、配对音频和参考素材在所有 H3 节点中的接法相同。
- `prompt_format` 为可选字段：缺省或 `narrative` 表示自然语言格式（如六模块编译结果）；`context_ir` 表示实际提示词采用 [context-ir-format.md](context-ir-format.md) 的官方六段结构；`h3_base` 表示实际提示词采用 [h3-base-format.md](h3-base-format.md) 的官方基础模式三字段结构。填 `context_ir` 或 `h3_base` 时脚本对 `prompt` 运行对应结构校验并把结果并入 findings；`h3_base` 还必须填 `h3_mode`（`t2va`/`i2va`/`fl2va`/`l2va`），缺省或非法值即阻断。`<Subject N>` 是语义标签不是附件，附件绑定仍只核对 `<Picture>`、`<Video>`、`<Audio>`。结构通过不证明语义或画面合格。
- 目标时长超过单次 H3 生成、含多镜/多角色/参考音频/长视频时，按 [h3-timeline-director.md](h3-timeline-director.md) 的强制触发条件编译 `segmentConfig`，并对实际 `timeline_data` 运行 `scripts/timeline_plan_check.py`；不能把整段任务写成一条 base prompt 后用“后期拼接”代替分段计划。多段只用于同一条连续动作的拆分，使用正重叠；真正的换机位/换场分别生成，按 [transition-causality.md](transition-causality.md) 设计切点，不用 0 重叠把独立镜头拼成一组。
- `max_by_kind` 是当前模型、模式和运行节点已核实的上限，不是全平台默认值；可对 `image`、`video`、`audio`、`other` 填非负整数或 `null`。未知上限必须保持未验证，超限不能默默截断。`capacity_evidence` 记录依据。
- 附件 `path` 为真实本地文件的绝对路径，不可读取时填 `null`。`sha256` 是预期投送版本，`review.sha256` 是批准记录绑定的版本，两者须对应实际文件字节；`review.status` 为 `approved`、`unverified` 或 `rejected`，`evidence` 指向实际审核记录。声明“已审核”不代替查看记录和图片；一张关键帧内包含多个人，也不自动证明各人物资产齐全。

## 运行与处理

```text
python scripts/prompt_preflight.py --input <本地提交记录.json>
```

程序不联网、不写入输入文件、不执行生成；仅接受可信的本地记录，读取其中明确指定的本地文件并计算 SHA-256。单份 JSON 最多 2 MB、最多 32 个附件、每个附件最多读取 512 MiB；无法读取、超限或读取时变化的文件标为待核。外部 URL 的真实字节无法由本工具验证。声明 `prompt_format: "context_ir"` 的记录还会运行 `context_ir_check.py` 的六段结构校验，声明 `"h3_base"` 的记录运行 `h3_base_check.py` 的基础模式校验；单独检查纯文本时可直接运行 `python scripts/context_ir_check.py --input <提示词.txt> [--duration 秒]` 或 `python scripts/h3_base_check.py --input <提示词.txt> --mode <t2va|i2va|fl2va|l2va> [--duration 秒]`，输出同样的 findings 结构。

它能检查所录入的锁定字符串、增补授权声明、资产状态声明、回退状态、容量、H3 显式标签、文件字节及批准哈希；检查对象受录入范围限制。`BLOCK` 或 `INVALID_INPUT` 退出码为 1；无阻断时仍是 `REVIEW_REQUIRED`、退出码为 2。脚本不会输出 `PASS`，因为它不理解剧情、不验收资产或图片、不确认真实接口是否使用了这份请求。

报告中的 `declared_payload_sha256` 对录入的模型、参数、最终文本、绑定方式及附件顺序/角色/实际字节散列；`source_prompt_sha256`、`prompt_sha256` 和 `input_sha256` 分别标识源、输出和记录。将该 `prompt_sha256` 与[逐镜结构检查](shot-audit-protocol.md)报告中对应镜头的 `prompts[].prompt_sha256` 逐项比较；单次提交含多镜时，各镜录入的是同一完整投送文本。任一不一致说明两门没有检查同一请求，修正后重跑。哈希不是服务器实际收到请求的证明。真正的生成网关必须以同一份请求及文件字节进行校验和提交，在边界重新核对；提示词、附件、参数、源事实或审批版本变化时重跑并重审。未接入网关时，这些规则由宿主执行，直接绕过 Skill 的调用不会被脚本拦截。

`BLOCK` 先回到编译、资产或导演责任层修复并重跑；回退、能力、附件、授权或人物清点未验证时，须补齐证据并独立复核，不能将退出码 2 当作提交许可。无论脚本结果如何，关键帧仍按 `keyframe-visual-review.md` 看真实图片，视频生成后仍看实际片段和相邻接缝。

## 参考

- [OpenH3-IR，所研究版本](https://github.com/ruashots/open-h3-ir/tree/fd031e136ae3d89147324c0d1b2aa65e838c21f5)：编译记录、声明与实际参考绑定、分级校验和回退的设计；非本包依赖。
- [MiniMax 官方 H3 Context-IR](https://platform.minimax.io/docs/api-reference/video-generation-v2-h3-context-ir)：官方增强服务与生成接口独立，实际调用需要单独授权。
