---
id: archive-20260816-public-revision-taxonomy
level: L2
summary: 公开文章栏目、筛选和计数只读发布修订，未发布 PATCH 不再改公开面
load_when:
  - task:20260816-public-revision-taxonomy
author: Gavin
task_id: 20260816-public-revision-taxonomy
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 公开 API 已声明只读发布修订，需要写明栏目/标签赋值同样走修订，避免下一轮再按工作副本实现。
state_history:
---

# 20260816-public-revision-taxonomy

Deterministic compressed record. The original active spec remains in Git history.

## Goal

已发布文章的公开栏目、标签筛选、taxonomy 计数和搜索 taxonomy 字段使用当前发布修订的赋值；工作副本改栏目/标签只影响管理编辑器与 `has_unpublished_changes`。同一栏目/标签的现场改名仍作用于该修订。

## Acceptance criteria

- AC-1: 文章发布在栏目 A / 标签 T 后，未发布 PATCH 到栏目 B / 标签 U，`GET /api/v1/articles/{y}/{m}/{slug}` 的 `category`/`tags` 仍是 A/T。
- AC-2: 同一状态下 `GET /api/v1/articles?category=` / `?tag=` 仍按 A/T 命中，不按 B/U 命中；`GET /api/v1/taxonomy` 计数留在 A/T。
- AC-3: 再次发布后，详情、筛选和计数才切到 B/U。
- AC-4: 已发布文章 PATCH 栏目/标签后，公开搜索仍按发布修订的栏目/标签名命中，直到再次发布或对该发布栏目/标签做改名同步。
- AC-5: `apps/api/README.md` 写明公开文章栏目/标签赋值来自当前发布修订，现场改名除外。

## Result

Verified and closed by the harness close command.

## Evidence

[20260816-public-revision-taxonomy.json](../../verification/evidence/20260816-public-revision-taxonomy.json)

Closed at 2026-08-16T11:29:04.682168+00:00.
