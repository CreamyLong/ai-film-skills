# 提示词编译、增强与素材绑定

## 适用范围

本流程借鉴 OpenH3-IR 的分离编译、限制增补、绑定引用、校验和回退留痕思路，以本包独立实现；不安装或调用该项目，也不声称等价于 MiniMax 官方 Context-IR。对实际视频生产的每个提交单元和重试，先完成 `submission-preflight.md` 与 `shot-audit-protocol.md`，再用本协议检查实际编译结果。纯文字咨询不因此启动生成、上传或付费。

增强是可选的转换，不是“细节越多越好”。以剧本、已批准导演包和用户锁定项为上限：对每个出场主体分别记录身份、是否活着、可见部位、当前动作和画面责任；记录景别、焦点、镜头、台词、声音及首尾状态。静止、无配乐、无对白和固定摄影机都可有效。只补执行需要且有依据的内容；对新增人物、事件、动作、表演、配乐、对白、画内文字或机位变化，标明出处和授权，冲突或未知则返修或待核。

特别注意“操作死者手部”：法医的手可以有操作动作，不代表法医的脸可见；死者的状态和手部焦点不能被另一位活人的表演模板覆盖。必须直接检查实际编译后的文本及其参考图片，不以标签齐全证明语义正确。

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
- `prompt_format` 为可选字段：缺省或 `narrative` 表示自然语言格式（如六模块编译结果）；`context_ir` 表示实际提示词采用 [context-ir-format.md](context-ir-format.md) 的官方六段结构。填 `context_ir` 时脚本对 `prompt` 运行结构校验并把结果并入 findings；`<Subject N>` 是语义标签不是附件，附件绑定仍只核对 `<Picture>`、`<Video>`、`<Audio>`。结构通过不证明语义或画面合格。
- `max_by_kind` 是当前模型、模式和运行节点已核实的上限，不是全平台默认值；可对 `image`、`video`、`audio`、`other` 填非负整数或 `null`。未知上限必须保持未验证，超限不能默默截断。`capacity_evidence` 记录依据。
- 附件 `path` 为真实本地文件的绝对路径，不可读取时填 `null`。`sha256` 是预期投送版本，`review.sha256` 是批准记录绑定的版本，两者须对应实际文件字节；`review.status` 为 `approved`、`unverified` 或 `rejected`，`evidence` 指向实际审核记录。声明“已审核”不代替查看记录和图片；一张关键帧内包含多个人，也不自动证明各人物资产齐全。

## 运行与处理

```text
python scripts/prompt_preflight.py --input <本地提交记录.json>
```

程序不联网、不写入输入文件、不执行生成；仅接受可信的本地记录，读取其中明确指定的本地文件并计算 SHA-256。单份 JSON 最多 2 MB、最多 32 个附件、每个附件最多读取 512 MiB；无法读取、超限或读取时变化的文件标为待核。外部 URL 的真实字节无法由本工具验证。声明 `prompt_format: "context_ir"` 的记录还会运行 `context_ir_check.py` 的六段结构校验；单独检查纯文本时可直接运行 `python scripts/context_ir_check.py --input <提示词.txt> [--duration 秒]`，输出同样的 findings 结构。

它能检查所录入的锁定字符串、增补授权声明、资产状态声明、回退状态、容量、H3 显式标签、文件字节及批准哈希；检查对象受录入范围限制。`BLOCK` 或 `INVALID_INPUT` 退出码为 1；无阻断时仍是 `REVIEW_REQUIRED`、退出码为 2。脚本不会输出 `PASS`，因为它不理解剧情、不验收资产或图片、不确认真实接口是否使用了这份请求。

报告中的 `declared_payload_sha256` 对录入的模型、参数、最终文本、绑定方式及附件顺序/角色/实际字节散列；`source_prompt_sha256`、`prompt_sha256` 和 `input_sha256` 分别标识源、输出和记录。将该 `prompt_sha256` 与[逐镜结构检查](shot-audit-protocol.md)报告中对应镜头的 `prompts[].prompt_sha256` 逐项比较；单次提交含多镜时，各镜录入的是同一完整投送文本。任一不一致说明两门没有检查同一请求，修正后重跑。哈希不是服务器实际收到请求的证明。真正的生成网关必须以同一份请求及文件字节进行校验和提交，在边界重新核对；提示词、附件、参数、源事实或审批版本变化时重跑并重审。未接入网关时，这些规则由宿主执行，直接绕过 Skill 的调用不会被脚本拦截。

`BLOCK` 先回到编译、资产或导演责任层修复并重跑；回退、能力、附件、授权或人物清点未验证时，须补齐证据并独立复核，不能将退出码 2 当作提交许可。无论脚本结果如何，关键帧仍按 `keyframe-visual-review.md` 看真实图片，视频生成后仍看实际片段和相邻接缝。

## 参考

- [OpenH3-IR，所研究版本](https://github.com/ruashots/open-h3-ir/tree/fd031e136ae3d89147324c0d1b2aa65e838c21f5)：编译记录、声明与实际参考绑定、分级校验和回退的设计；非本包依赖。
- [MiniMax 官方 H3 Context-IR](https://platform.minimax.io/docs/api-reference/video-generation-v2-h3-context-ir)：官方增强服务与生成接口独立，实际调用需要单独授权。
