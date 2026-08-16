---
id: spec-20260816-public-revision-taxonomy
level: L1
summary: 公开文章栏目、筛选和计数只读发布修订，未发布 PATCH 不再改公开面
load_when:
  - task:20260816-public-revision-taxonomy
author: Gavin
task_id: 20260816-public-revision-taxonomy
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 公开 API 已声明只读发布修订，需要写明栏目/标签赋值同样走修订，避免下一轮再按工作副本实现。
state_history:
---

# Context

2026-08-16 审计 AUD26-017：公开文章标题/正文/详情标签走 `ArticleRevision`，但 `_revision_category`、`GET /articles?category|tag` 和 `GET /taxonomy` 计数 join 工作副本外键。未发布的栏目 PATCH 会改公开卡片、筛选和计数，同时编辑器显示「有未发布修改」。

# Goal

已发布文章的公开栏目、标签筛选、taxonomy 计数和搜索 taxonomy 字段使用当前发布修订的赋值；工作副本改栏目/标签只影响管理编辑器与 `has_unpublished_changes`。同一栏目/标签的现场改名仍作用于该修订。

# Non-goals

- 不改项目/书摘快照模型。
- 不改已发布 slug 锁定、发布 version 校验或导出（第三批）。
- 不改两条 GitHub frozen spec。
- 不把未分类文章算进「全部文章」栏目计数之和（AUD26-036）。

# Acceptance criteria

- AC-1: 文章发布在栏目 A / 标签 T 后，未发布 PATCH 到栏目 B / 标签 U，`GET /api/v1/articles/{y}/{m}/{slug}` 的 `category`/`tags` 仍是 A/T。
- AC-2: 同一状态下 `GET /api/v1/articles?category=` / `?tag=` 仍按 A/T 命中，不按 B/U 命中；`GET /api/v1/taxonomy` 计数留在 A/T。
- AC-3: 再次发布后，详情、筛选和计数才切到 B/U。
- AC-4: 已发布文章 PATCH 栏目/标签后，公开搜索仍按发布修订的栏目/标签名命中，直到再次发布或对该发布栏目/标签做改名同步。
- AC-5: `apps/api/README.md` 写明公开文章栏目/标签赋值来自当前发布修订，现场改名除外。

# Risks

按修订筛选后，工作副本已换栏目的文章在公开轨上仍显示旧栏目，这是有意的；管理列表继续显示工作副本。

# Verification plan

- api-lint => AC-1, AC-2, AC-3, AC-4, AC-5
- api-tests => AC-1, AC-2, AC-3, AC-4, AC-5
