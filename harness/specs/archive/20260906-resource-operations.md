---
id: archive-20260906-resource-operations
level: L2
summary: 完成视觉提案第五阶段的后台资源与运营
load_when:
  - task:20260906-resource-operations
author: Gavin
task_id: 20260906-resource-operations
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/README.md
  - ui-fix/PHASE-5.md
documentation_reason: 记录五个运营页、资源复用、失败恢复和助手独立准入的实现与验收边界。
evidence_sha256: 68747231d2d280d4a7e65e4c4eedfe9272355e022a004f5d09e75f104942cd99
state_history:
---

# 20260906-resource-operations

Deterministic compressed record. The original active spec remains in Git history.

## Goal

使用真实接口完成五页的资源优先布局、反馈与双主题手机适配，并验证管理到公开页面及编辑器的闭环。

## Acceptance criteria

- AC-1: 五页沿用现有主题字体，资源与操作分区清楚，320–1440px、短视口、长文本和双主题下无页面横滚，键盘可达且费用各项有明确标签。
- AC-2: 隔离数据上的名片和栏目变更反映到公开页；媒体上传、外链、筛选、移除恢复和引用到编辑器正常，操作及剪贴板失败可见且可重试。
- AC-3: 导入只创建草稿并提供编辑入口，导出与回收站恢复/永久删除使用真实接口，失败保留准确反馈和重试路径。
- AC-4: 助手部署、入口、管理员请求与实际准入分别显示，未知保持未知；本地刷新、停用及重建操作保持原有版本、确认和资格边界。
- AC-5: 五页覆盖、设计能力差异、紧凑验证证据与回退方式可复查，并通过确定性归档。

## Result

Verified and closed by the harness close command.

## Evidence

[20260906-resource-operations.json](../../verification/evidence/20260906-resource-operations.json)

SHA-256: `68747231d2d280d4a7e65e4c4eedfe9272355e022a004f5d09e75f104942cd99`

Closed at 2026-09-05T20:51:57.467073+00:00.
