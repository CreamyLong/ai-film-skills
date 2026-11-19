# 可选：Qwen-MM-Plugins 能力补强

`QwenLM/Qwen-MM-Plugins` 不是模型升级，而是一组把多模态模型包成 MCP 工具/Skill 的插件。它能补上单次 omni 调用做不到的**分轨、时间定位、长视频记忆和专用识别**。以下为可选外部能力，本 Skill 不依赖它也能完成 T1–T6。

## 1. 值得接的四个

| 缺口 | 插件/工具 | 实测 |
|---|---|---|
| 说话人分离 + 时间戳转写 | `api` → `omni_multi_speaker_asr` | 已用本仓库密钥跑通，返回 `Speaker 0` + 起止秒 + 文本 |
| 纯转写 / SRT | `api` → `omni_asr_timestamped` | 支持 json / srt |
| 图片文字与目标框 | `api` → `ocr`、`grounding` | OCR 可读画面文字；grounding 返回像素/归一化框 |
| 事件起止与计数 | `api` → `omni_av_grounding`、`omni_av_counting` | 给文本查询，返回时间段/次数 |
| 30 秒窗口的音视频记忆 | `omni-memory` | 每窗记录画面描述、每句台词的说话人/语气/环境声，可按人检索 |
| 长视频/整季记忆 | `video-memory` | >30 分钟素材建树，支持实体/事件/OCR/ASR 检索 |

## 2. 不该指望它解决的

- 它只给证据（转写、时间、框），**不给严重度和判决**；blocker/major 仍按本 Skill 的 `verdict-schema.md` 判。
- OCR 会把伪字“读顺”（实测一帧乱码档案袋被读成「档案袋」），**不能单独用来判伪文字**；要和画面复核配对。
- ASR 是句级时间，不是词级；口型核对仍需抽帧。
- 默认模型是 `qwen3.5-omni-plus` / `qwen3.7-plus`，与 `qwen3.8-omni-flash` 的判词习惯不同；结果要重新校准。

## 3. 运行方式

插件可以独立作为 MCP server 启动，不必绑定 Claude Code/Codex：

```bash
uvx --from "qwen-mm-plugins[api] @ git+https://github.com/QwenLM/Qwen-MM-Plugins.git" \
  qwen-mm-plugins-api
```

- 需要 `uv`/`uvx`、`ffmpeg`；云端调用需要 `DASHSCOPE_API_KEY`。
- 配置写在 用户主目录下的 `.qwen-mm-plugins/config`；环境变量优先。
- `omni-memory` 构建会在视频旁生成 `<video>.memory/`，含实体、事实、30 秒事件、场景与片段。
- 长视频建库耗时：一小时素材约 10–40 分钟，取决于是否用 OSS。

## 4. 建议接法

1. **对白完整性/鬼声**：对每集音轨跑 `omni_multi_speaker_asr`，核对台词是否完整、说话人是否串、静帧下是否还有上一句残留。
2. **字幕与文字**：用 `ocr` 批量读抽帧，定位烧录字幕；伪字仍回 T2 人工看。
3. **空间/事件时间**：用 `omni_av_grounding` 找“法槌落下”“车门关闭”等事件的起止，和剪辑点对齐。
4. **跨集连续性**：整季用 `video-memory` 建一次记忆，查同一角色/道具/场景的跨集漂移。
5. **判决**：所有插件输出进本 Skill 的 `review_required`，由人确认后才改 `reviewed`。

## 5. 边界

- 上传素材到外部服务前确认授权；密钥只走环境变量。
- 插件版本变化会改工具名和 schema；接入时锁定 git tag，并保留调用记录。
- 不因为“装了插件”就声称审查通过；覆盖层与人工确认仍是必需的。
