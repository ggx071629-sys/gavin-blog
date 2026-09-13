---
id: archive-20260815-related-article-copy
level: L2
summary: 去掉公开文章相关区泄漏的布局实现词，改成读者可读文案
load_when:
  - task:20260815-related-article-copy
author: Gavin
task_id: 20260815-related-article-copy
status: compressed
documentation_impact: none
documentation_reason: 只替换读者可见文案，不改变阅读页块顺序、公开契约或 Web 边界中的 chrome 描述。
state_history:
---

# 20260815-related-article-copy

Deterministic compressed record. The original active spec remains in Git history.

## Goal

读者在公开文章页只看到中文阅读文案，不再看到布局实现词。

## Acceptance criteria

- AC-1: `/notes/{year}/{month}/{slug}` 相关区可见标题为「相关文章」，页面源码与可见文本都不含 `adaptive`。
- AC-2: 章节概览轨可见标题为「章节概览」，不再显示 `Article signal`。
- AC-3: Web 单元或阅读页 E2E 断言上述文案，且现有相关推荐 `data-count` 行为保持。

## Result

Verified and closed by the harness close command.

## Evidence

[20260815-related-article-copy.json](../../verification/evidence/20260815-related-article-copy.json)

Closed at 2026-08-15T16:32:48.525260+00:00.
