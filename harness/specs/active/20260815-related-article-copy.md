---
id: spec-20260815-related-article-copy
level: L1
summary: 去掉公开文章相关区泄漏的布局实现词，改成读者可读文案
load_when:
  - task:20260815-related-article-copy
author: Gavin
task_id: 20260815-related-article-copy
status: active
verification_profile: focused
documentation_impact: none
documentation_reason: 只替换读者可见文案，不改变阅读页块顺序、公开契约或 Web 边界中的 chrome 描述。
state_history:
---

# Context

2026-08-15 审计 AUD26-004：公开文章相关区把 V2 布局说明 `adaptive single item` / `adaptive N items` 直接渲染给读者，章节轨还有无中文对照的 `Article signal`。公开文章 API 契约不变。

# Goal

读者在公开文章页只看到中文阅读文案，不再看到布局实现词。

# Non-goals

- 不改相关推荐数量、网格自适应或公开 `/articles` 与 `/context` 契约。
- 不改参考资料、反链、相邻文章的数据来源。
- 不改两条 GitHub frozen spec。

# Acceptance criteria

- AC-1: `/notes/{year}/{month}/{slug}` 相关区可见标题为「相关文章」，页面源码与可见文本都不含 `adaptive`。
- AC-2: 章节概览轨可见标题为「章节概览」，不再显示 `Article signal`。
- AC-3: Web 单元或阅读页 E2E 断言上述文案，且现有相关推荐 `data-count` 行为保持。

# Risks

公开阅读文案变化。不改 API、数据或认证。

# Verification plan

- web-quality => AC-1, AC-2, AC-3
- api-lint => AC-1
- api-tests => AC-1
