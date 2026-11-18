# 抽卡候选资产的保留、隔离与授权清理

用于实际媒体生产后的磁盘治理。目标是减少失败候选占用的空间，同时保留可追溯性和回退能力；不是让 Agent 按文件名猜测并批量删除。

## 1. 公开实践的核对结论

本规则参考了公开实现，但不声称它们支持“自动删除废片”：

- `zenstory-ai/drama-skills` 的 `short-drama-review` 把生成媒体分为保留沿用、裁切避让、后期修补、建议重抽和整批退回；`short-drama-edit` 的 `EDT-11` 要求逐镜登记未入片原因。它保留处置记录，不要求自动删除媒体。
- `kajisho5/ffmpeg-skill` 要求保留原文件、先 `--dry-run`，只清理本工具执行产生的半成品；其事故记录说明，仅凭“输出路径存在”清理文件可能误删用户已有交付物。
- 因此，本包采用“**审核标废 + 保留替代 + 干跑 + 明确授权 + 哈希复核**”作为本项目扩展，不把自动删除说成上述项目的既有规则。

## 2. 生命周期

| 状态 | 含义 | 媒体处理 |
|---|---|---|
| `candidate` | 尚未完成内容审核 | 保留；不得进入清理清单 |
| `accepted` | 当前采用或已批准 | 保留；不得清理 |
| `rejected` | 已审不合格，尚无采用价值 | 满足第 3 节全部条件后才可清理 |
| `superseded` | 已有新 accepted take 替代 | 满足条件后可清理 |
| `failed_partial` | 本次工具调用实际产生的半成品 | 能证明归属且未被引用时可清理 |
| `archived` / `deleted` | 已执行隔离或删除 | 保留清单、原因、哈希和报告 |

**媒体可以删，证据不能删。** 提示词、种子、参考版本、生成记录、QC 结论、未入片原因和清理报告都是小型文本，继续保留。

## 3. 硬规则

1. **未审不删。** 只有 `rejected`、`superseded`、`failed_partial` 可进入清理候选；`candidate`、`accepted` 一律阻断。
2. **唯一可用镜不删。** 每个 `shot_id` 必须在 `retained` 中指定一个仍存在的 accepted/fallback 文件；整镜放弃时逐项写 `orphan_allowed: true` 和叙事原因。
3. **引用存在不删。** 当前 EDL/editlist、组装报告、锁定时间线或交付清单仍引用该文件时阻断。清理器同时按参考文件所在目录及其上级目录解析相对媒体路径。
4. **输入与资产不删。** 人物、场景、道具、音色参考、上传源视频、剧本和已批准资产不属于 generated candidate；`generated_roots` 必须显式限定在生成候选目录。
5. **审核后变化不删。** 清单记录审核时 SHA-256；执行前重新计算，不一致报 `FILE_CHANGED_SINCE_REVIEW`。
6. **在制任务不删。** 默认文件年龄至少 24 小时；仍在队列、正在写入或刚生成的文件由 `TOO_RECENT` 阻断。不要用降低年龄阈值绕过在制保护。
7. **先干跑，再授权。** 默认只输出计划；`--execute` 才动作，永久删除还必须 `--yes`。Agent 不因本文件获得删除授权，每一批实际删除都要有用户对该批清单的明确同意。
8. **不删目录，不递归清空。** 只处理清单逐项列出的普通文件；符号链接、目录、重复项和越界路径均阻断。
9. **失败留报告。** 任一 blocked 项要修复清单或保留文件，不得手工绕过报告另删。清理后记录实际删除/归档数量与释放字节。

## 4. 清单合同

```json
{
  "version": 1,
  "project_root": "/ABS/PROJECT_ROOT",
  "generated_roots": ["制作/EP007/video/v1"],
  "reference_files": [
    "制作/EP007/edit/editlist.json",
    "制作/EP007/edit/assembly-report.json"
  ],
  "archive_dir": "制作/_rejected_assets/2026-11-18",
  "retained": [
    {"path": "制作/EP007/video/v1/shot07_fix.mp4", "shot_id": "07"}
  ],
  "items": [
    {
      "path": "制作/EP007/video/v1/shot07.mp4",
      "shot_id": "07",
      "status": "superseded",
      "sha256": "审核时实际文件的64位SHA-256",
      "reason": "音色不统一，已由fix版替代",
      "evidence": "制作/EP007/edit/QC_REPORT.md"
    }
  ]
}
```

- `project_root` 必须是真实绝对目录；其余路径相对它解析，越界即拒绝。
- `reference_files` 不能为空，可为 JSON 或文本；至少列入当前 EDL/资产登记/QC 文件。JSON 递归读取字符串，文本提取媒体路径。
- `retained` 文件必须真实存在；它是替代镜/保底镜证明，不是形式字段。
- `evidence` 必须指向实际看片/听辨或工具失败记录；不能只写“文件太多”。

## 5. 执行

```bash
# 默认 dry-run：不写、不移、不删；先看 planned/blocked 和可回收字节
python3 scripts/generation_asset_gc.py \
  --manifest edit/cleanup-manifest.json \
  --report edit/cleanup-dry-run.json

# 经本轮授权后隔离：移动到 archive_dir，保留相对目录结构
python3 scripts/generation_asset_gc.py \
  --manifest edit/cleanup-manifest.json \
  --mode archive --execute --report edit/cleanup-archive-report.json

# 经本轮明确删除授权后永久删除；--yes 不可省略
python3 scripts/generation_asset_gc.py \
  --manifest edit/cleanup-manifest.json \
  --mode delete --execute --yes --report edit/cleanup-delete-report.json
```

归档便于回退，但不等于释放同一磁盘的空间；要释放空间需明确选择 delete。报告原子写入。存在任一 blocked 时拒绝整批执行，不改变任何媒体；先修清单再重新 dry-run。退出码：`0` 无 blocked，`1` 有 blocked，`2` 清单或执行错误。

## 6. 与剪辑和交付的衔接

- 素材筛选阶段先登记诊断状态和替代关系，不因一次失败立即删除；返修期间保留可回退版本。
- 当前 editlist 改指向新 take 后，旧 take 才能以 `superseded` 进入候选；组装与QC报告生成后再跑引用检查。
- 锁画、声音交接或最终交付后，被锁版本引用的媒体继续保留；清理只针对未引用候选。
- 项目归档时按授权决定保留期限和备份目标；本规则不改变交付合同，也不把“文件已删除”当作“镜头已验收”。
