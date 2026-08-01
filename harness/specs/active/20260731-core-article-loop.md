---
id: spec-20260731-core-article-loop
level: L1
summary: 完成单管理员从草稿写作、自动保存、预览、发布到公开阅读的核心文章闭环
load_when:
  - task:20260731-core-article-loop
author: Gavin
task_id: 20260731-core-article-loop
status: verified
---

# Core article loop

## Context

Harness 已建立，但产品代码仍为空。第一阶段需要证明 Nuxt、FastAPI 与 SQLite 的真实跨端闭环，并为后续内容系统保留稳定边界。

## Goal

单管理员可以安全登录，创建文章草稿，在 Markdown 编辑器中自动保存与预览，发布后通过 `/notes/{year}/{month}/{slug}` 公开阅读。首页和文章页只展示已发布内容。

## Non-goals

- 栏目、标签、项目、读书笔记、FTS5 搜索。
- 媒体上传、图片转换与对象存储。
- 回收站、Markdown 批量导入导出。
- RSS、站点地图、完整 SEO、Lighthouse 90+ 打磨。
- 部署、CI 与生产基础设施。

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

## Risks

- 自动保存可能覆盖较新的内容，因此 API 使用乐观锁版本号。
- Cookie 与跨端开发端口会影响认证，因此本地通过明确 CORS 与 credentials 边界处理。
- Markdown 输出可能包含不可信 HTML，因此禁用原始 HTML并清洗最终输出。
- 当前无 Git 历史；完成验证后 spec 暂不执行 close，直到原文进入 Git HEAD。

## Verification plan

- Alembic 在临时 SQLite 数据库执行到最新版本。
- Pytest 执行完整 API 集成闭环。
- Vitest 验证日期 URL、自动保存状态与 Markdown 工具。
- Nuxt 执行类型检查与生产构建。
- Playwright 在本地双服务启动后执行核心闭环。
- Harness 重新生成索引并产出 `20260731-core-article-loop` evidence。

## Implementation record

- Nuxt Web、FastAPI API 与 OpenAPI 契约边界已初始化。
- 核心文章闭环、认证防护、乐观锁与 Markdown 渲染已实现。
- 2026-08-02 发布候选门禁再次通过 API、Vitest、类型、构建与核心 Playwright 旅程；spec 已具备关闭条件，等待原文进入首个 Git HEAD 后执行确定性归档。
