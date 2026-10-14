# Shared add-on development

For RR Helper or Character Designer requests, the canonical development sources
are under `D:\MyRepository\Blender-addons-by-Randy\addons`. Read that repository's
`AGENTS.md` and make plugin code changes there, even when this task starts in X.

This project's `addons/character_designer` is a validation/deployment copy.
Update it from the shared repository with its `tools/deploy_local.py
--project-addons D:\Blender\Projects\Character\X\addons`, and verify using `--check`.
Do not edit the copy first and copy changes back into the repository.

Character assets, scene work, and real-model integration checks remain in X.

# Save completed scene work

The user asks that completed Blender scene operations be saved. After authorized
scene work, save the current artist `.blend` and verify Blender reports success.
Keep isolated test scenes separate. Saving does not authorize applying a pending
model repair or choosing a repair direction for the artist.

# Performance history and ownership

X owns Character Designer scene integration and its optimization records.
For follow-up Original20 return/integration work, begin with
`validation/composition_20261011/fresh_rigging_round_20261012/current_return_summary.json`.
It indexes accepted evidence. The older `current_return_checkpoint.json` contains
historical intermediate versions, processes and pending states; do not treat
those as current work. Observe the live artist identity again before new scene
operations. External file pins can be checked without Blender using the shared
repository's `tools/verify_file_pin.py`; file identity alone is not scene-operation
authorization.
Before another performance investigation, read
`D:\Codex\資料庫\电脑与工作环境\Blender性能優化台帳.md` and follow its
evidence links; target new symptoms or changed code rather than repeating all
previous checks. Append the date, source/runtime versions, verified model and
reasoning effort (unknown means unrecorded), comparable measurements, validation
limits, deployment/refresh/save state and the next investigation trigger.
Keep raw project evidence here and index it in the existing Codex Console
database. Builder6 / Build WIP owns RR Helper; RandomRealm2 owners retain their
project evidence and the existing Unity performance-history entry points.

# 历史诊断报告的缩减（用户 2026-10-14 授权）

- 日常保留小型结论、实际变化、输入/版本/文件哈希及重现入口，不默认把每个阶段的完整顶点、权重、Shape Key 数组反复写进上传报告。旧的中间检查可大幅缩减；重要性按当前采用情况、依赖和未解决问题判断，不能只按日期批量删除。
- 完整原始证据需要保留时，先无损压缩到本项目 `.validation-archives/`，逐字节校验还原 SHA256 与长度，再生成带独立 summary schema、原始哈希、本机档案位置的摘要。该目录不参与 Git 日常上传；远端只有摘要时必须如实说明。
- 已经被重放脚本、accepted manifest/receipt 固定哈希引用的原始输入，以及最新验收、失败现场和恢复依据，不能用报告瘦身流程随意改写。保留已有文件引用，摘要注明字段路径属于原始档案和对应阶段。
- 本次 Original leave 三阶段历史报告使用 `tools/compact_validation_report.py`。默认只预览；实际应用必须提供核对后的源 SHA256；工具先验证 XZ 完整还原、保护源文件写入和并发，再替换摘要。不运行 Blender，不保存场景，不修改 Git 暂存区，不提交或推送，也不改写已有提交。
- X 聊天已于 2026-10-14 只读核对并同意此次单份摘要替换，无需恢复；完整 XZ、原运行日志、当前验收引用、失败现场/恢复依据、场景备份、固定哈希重放输入及源码/manifest/receipt 必须保留。其他报告仍需逐份核对，不能沿用本次认可批量删除。
