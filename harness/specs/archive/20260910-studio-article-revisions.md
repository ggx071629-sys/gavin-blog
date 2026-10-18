---
id: archive-20260910-studio-article-revisions
level: L2
summary: 文章发布历史采用清晰版本列表与快照差异阅读区
load_when:
  - task:20260910-studio-article-revisions
task_id: 20260910-studio-article-revisions
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录本任务页面的设计实现及实际行为边界。
evidence_sha256: 17c6fbf11c8977f8f55c5dba3963bb731847da561e69e6ee76ff43f1d5990acb
state_history:
---

# 20260910-studio-article-revisions

Deterministic compressed record. The original active spec remains in Git history.

## Goal

文章发布历史采用清晰版本列表与快照差异阅读区

## Acceptance criteria

- AC-1: 版本页返回编辑、预览工作副本、当前发布说明及可选版本列表清晰；桌面双栏手机上下排列，快照与差异可读。
- AC-2: 真实版本加载、查看快照、与当前比较、取消回滚和确认新修订、错误恢复均通过验证，双主题窄屏无溢出。

## Result

Verified and closed by the harness close command.

## Evidence

[20260910-studio-article-revisions.json](../../verification/evidence/20260910-studio-article-revisions.json)

SHA-256: `17c6fbf11c8977f8f55c5dba3963bb731847da561e69e6ee76ff43f1d5990acb`

Closed at 2026-09-10T09:25:32.857332+00:00.
