---
id: archive-20260910-studio-content-tools
level: L2
summary: 回收站恢复删除与 Markdown 迁移分区
load_when:
  - task:20260910-studio-content-tools
task_id: 20260910-studio-content-tools
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录本任务页面的设计实现及实际行为边界。
evidence_sha256: 3161c795d6b4034ff7851aa126f4152fa72a9727f6c23aa80372ec6465d77bd7
state_history:
---

# 20260910-studio-content-tools

Deterministic compressed record. The original active spec remains in Git history.

## Goal

回收站恢复删除与 Markdown 迁移分区

## Acceptance criteria

- AC-1: 回收站采用开放记录、真实本页数量与恢复/永久删除操作，取消和失败保留内容。
- AC-2: Markdown 导入只创建草稿、导出真实 ZIP，失败可重试；两区及长文本在双主题窄屏可用。

## Result

Verified and closed by the harness close command.

## Evidence

[20260910-studio-content-tools.json](../../verification/evidence/20260910-studio-content-tools.json)

SHA-256: `3161c795d6b4034ff7851aa126f4152fa72a9727f6c23aa80372ec6465d77bd7`

Closed at 2026-09-10T11:21:49.409270+00:00.
