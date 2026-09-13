---
id: archive-20260827-cancel-public-penpot-specs
level: L2
summary: 取消八个未完成的公开页面 Penpot 对齐规格，并从博客主项目开放规格列表移除
load_when:
  - task:20260827-cancel-public-penpot-specs
author: Gavin
task_id: 20260827-cancel-public-penpot-specs
status: compressed
documentation_impact: required
documentation_targets:
  - README.md
  - harness/docs/decisions/20260827-cancel-public-penpot-specs.md
documentation_reason: 八个公开页面对齐任务不再推进，需要长期记录取消而非完成的语义、保留范围和未来重新立项边界。
state_history:
---

# 20260827-cancel-public-penpot-specs

Deterministic compressed record. The original active spec remains in Git history.

## Goal

以“取消、未完成”的语义从博客主项目开放规格列表移除八个公开页面 Penpot 规格，由 Git 历史和长期 ADR 保留原始边界与取消原因；不关闭旧任务、不删除现有 UI/QA 工作树修改，并保留未被用户列出的 Admin Login Penpot 规格继续处于 active。

## Acceptance criteria

- AC-1: 除本清理规格外，`harness/specs/active/` 和生成索引不再包含用户列出的八个 task ID；`20260827-admin-login-penpot-alignment` 保持 active，frozen 计数保持 0。
- AC-2: 主项目不为八个旧 task ID 新增 compressed spec、passed evidence 或 `spec.completed` 事件；长期 ADR 明确它们未完成、不可恢复、原文由 Git 历史保留。
- AC-3: 长期 ADR 明确当前未提交 UI/QA/evidence 不随规格删除，也不因此获得完成或可合入状态；未来若继续任何页面对齐，必须按当时产品基线创建新 task/spec。
- AC-4: 根 README 将公开页面 Penpot 批次标记为已取消，并准确说明仍保留的 Admin Login active spec；生成索引和全局 Harness 完整性检查通过。

## Result

Verified and closed by the harness close command.

## Evidence

[20260827-cancel-public-penpot-specs.json](../../verification/evidence/20260827-cancel-public-penpot-specs.json)

Closed at 2026-08-27T14:42:43.306225+00:00.
