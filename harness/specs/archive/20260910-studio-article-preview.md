---
id: archive-20260910-studio-article-preview
level: L2
summary: 文章草稿预览接入 Studio 阅读工作副本与返回编辑导航
load_when:
  - task:20260910-studio-article-preview
task_id: 20260910-studio-article-preview
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录本任务页面的设计实现及实际行为边界。
evidence_sha256: d1f948cc7427862b36d5945e80ed2ff10dfbfc18c16dbf1a2bed206ab578aab9
state_history:
---

# 20260910-studio-article-preview

Deterministic compressed record. The original active spec remains in Git history.

## Goal

文章草稿预览接入 Studio 阅读工作副本与返回编辑导航

## Acceptance criteria

- AC-1: 预览使用 Studio 外壳、清晰工作副本标记和返回编辑/版本历史入口，保留真实正文、目录、代码复制与单一一级标题。
- AC-2: 草稿及已发布未更新副本均读取真实数据且不改变公开版本；返回编辑保留已保存内容，双主题与窄屏可读。

## Result

Verified and closed by the harness close command.

## Evidence

[20260910-studio-article-preview.json](../../verification/evidence/20260910-studio-article-preview.json)

SHA-256: `d1f948cc7427862b36d5945e80ed2ff10dfbfc18c16dbf1a2bed206ab578aab9`

Closed at 2026-09-10T09:16:51.267502+00:00.
