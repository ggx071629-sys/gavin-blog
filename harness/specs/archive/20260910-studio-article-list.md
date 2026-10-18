---
id: archive-20260910-studio-article-list
level: L2
summary: 文章列表接通真实查询并对齐开放行设计
load_when:
  - task:20260910-studio-article-list
task_id: 20260910-studio-article-list
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录列表查询、状态提示和操作布局。
evidence_sha256: 840a6e2c90dae790b25f34ee15a96dc8f2326f55dceaabb49e68fe8e4684af8a
state_history:
---

# 20260910-studio-article-list

Deterministic compressed record. The original active spec remains in Git history.

## Goal

文章采用开放行、真实查询和状态计数、低频操作入口，保留分页与删除确认。

## Acceptance criteria

- AC-1: 文章搜索与状态筛选先于服务端分页，切换条件回第一页，分页和历史返回保留条件；错误可重试、空态可清除。
- AC-2: 文章开放行展示真实栏目、版本、未发布提示，编辑/预览/历史/删除可达，双主题手机桌面无横溢且通过 axe。

## Result

Verified and closed by the harness close command.

## Evidence

[20260910-studio-article-list.json](../../verification/evidence/20260910-studio-article-list.json)

SHA-256: `840a6e2c90dae790b25f34ee15a96dc8f2326f55dceaabb49e68fe8e4684af8a`

Closed at 2026-09-10T08:29:16.645517+00:00.
