---
id: archive-20260910-studio-book-list
level: L2
summary: 读书列表对齐设计并接通完整书名作者查询
load_when:
  - task:20260910-studio-book-list
task_id: 20260910-studio-book-list
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/public/studio/README.md
documentation_reason: 记录读书元信息与查询入口。
evidence_sha256: 04b7c5b54250c7a628b55bab7e408f92c110f8a5beab469edf3c020a7bc26f7d
state_history:
---

# 20260910-studio-book-list

Deterministic compressed record. The original active spec remains in Git history.

## Goal

读书列表采用统一开放行及书名/作者搜索，保留阅读状态和版本操作。

## Acceptance criteria

- AC-1: 读书书名/作者、阅读状态和发布状态显示真实数据，作者查询、状态筛选、删除失败恢复可用。
- AC-2: 双主题手机桌面布局无横溢且 axe 通过，编辑及公开版本入口真实，不出现文章专属历史入口。

## Result

Verified and closed by the harness close command.

## Evidence

[20260910-studio-book-list.json](../../verification/evidence/20260910-studio-book-list.json)

SHA-256: `04b7c5b54250c7a628b55bab7e408f92c110f8a5beab469edf3c020a7bc26f7d`

Closed at 2026-09-10T08:32:07.157176+00:00.
