---
id: archive-20260731-core-article-loop
level: L2
summary: 完成单管理员从草稿写作、自动保存、预览、发布到公开阅读的核心文章闭环
load_when:
  - task:20260731-core-article-loop
author: Gavin
task_id: 20260731-core-article-loop
status: compressed
---

# 20260731-core-article-loop

Deterministic compressed record. The original active spec remains in Git history.

## Goal

单管理员可以安全登录，创建文章草稿，在 Markdown 编辑器中自动保存与预览，发布后通过 `/notes/{year}/{month}/{slug}` 公开阅读。首页和文章页只展示已发布内容。

## Acceptance criteria

- FastAPI 使用 SQLite、SQLAlchemy 2.0 与 Alembic 保存文章和服务端 Session。
- 登录采用 HttpOnly Session Cookie、双提交 CSRF、防暴力登录限流，无公开注册。
- 管理员可以创建草稿并通过带版本号的 PATCH 自动保存，冲突返回 409。
- 编辑器提供保存状态、Markdown 预览和明确的发布动作。
- 发布文章拥有稳定的 `/notes/YYYY/MM/slug` URL；草稿不会出现在公开 API。
- Markdown 至少支持 GFM、代码高亮、目录、脚注、提示块、Mermaid 与 KaTeX。
- Nuxt 提供首页、文章列表、公开详情、登录、后台列表、编辑与预览页面。
- Pytest 覆盖认证、CSRF、草稿、冲突、发布和公开读取。
- Vitest 覆盖前端核心工具；Playwright 描述登录到公开阅读的用户闭环。
- OpenAPI 快照保存到 `packages/contracts/openapi.json`。

## Result

Verified and closed by the harness close command.

## Evidence

[20260731-core-article-loop.json](../../verification/evidence/20260731-core-article-loop.json)

Closed at 2026-08-01T16:41:15.346222+00:00.
