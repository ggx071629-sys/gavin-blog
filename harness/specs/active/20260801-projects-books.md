---
id: spec-20260801-projects-books
level: L1
summary: 打通项目与读书笔记从草稿编辑、自动保存、发布到公开阅读的纵向闭环
load_when:
  - task:20260801-projects-books
author: Gavin
task_id: 20260801-projects-books
status: verified
---

# Projects and book notes

## Context

第二阶段已完成文章栏目与标签。产品基线要求项目拥有独立详情页并可关联相关文章，读书笔记记录书籍、作者、封面、阅读状态、日期和评分；两种内容都应进入现有单管理员写作与公开阅读体系。

## Goal

单管理员可以创建、自动保存、预览并发布项目与读书笔记；公开读者可以通过 `/projects/{slug}` 和 `/books/{year}/{month}/{slug}` 浏览已发布内容，项目页展示已发布的关联文章。

## Non-goals

- 媒体上传与封面转换；本任务只保存外部封面 URL。
- 项目里程碑、团队成员、技术栈字典和复杂时间线。
- 书籍数据库、ISBN 查询和第三方元数据抓取。
- FTS5 搜索、回收站与 Markdown 导入导出。
- 项目或读书笔记的栏目、标签与评论。

## Acceptance criteria

- Alembic 新增项目、读书笔记和项目文章关联表；slug 在各自内容类型内唯一。
- 项目包含标题、slug、摘要、Markdown、仓库 URL、站点 URL、版本、草稿／发布状态及关联文章。
- 读书笔记包含书名、作者、slug、封面 URL、阅读状态、阅读日期、1–5 分评分、摘要、Markdown、版本和草稿／发布状态。
- 管理 API 支持两种内容的列表、创建、读取、带版本号 PATCH 自动保存和显式发布；变更受 Session 与 CSRF 保护，陈旧版本返回 `409`。
- 无效文章关联、阅读状态或评分返回 `422`；slug 冲突返回 `409`。
- 公开 API 和页面永不返回草稿；项目详情只暴露已发布的关联文章。
- Nuxt 提供项目与读书笔记的公开列表、详情，以及管理列表、新建、实时 Markdown 预览、保存状态和发布界面。
- 主导航与管理导航包含项目和读书笔记入口。
- Pytest 覆盖迁移、权限、关联、字段验证、乐观锁、发布和公开隔离；Playwright 覆盖两种内容的关键用户闭环。
- OpenAPI 快照与前端 TypeScript 契约同步。

## Risks

- 项目可能关联草稿文章，因此公开响应必须二次过滤文章发布状态。
- 两种编辑器的自动保存可能覆盖更新，因此沿用版本号乐观锁和明确的冲突状态。
- 外部 URL 可能无效或使用危险协议，因此只接受 Pydantic 可验证的 HTTP(S) URL，前端不渲染任意 HTML。
- 阅读状态与评分容易产生无效组合；本任务约束状态枚举和评分范围，但不强制完成状态必须评分。

## Verification plan

- 在隔离 SQLite 数据库将 Alembic 升级到 head 并检查新增表。
- Pytest 执行现有回归与项目／读书笔记集成测试。
- Ruff、Vitest、Nuxt typecheck 与生产构建通过。
- Playwright 验证管理员发布项目和读书笔记后可通过公开 URL 阅读，并验证项目关联文章。
- 重新生成 OpenAPI 快照。
- 运行 `python -m tools.harness index` 与 `python -m tools.harness verify 20260801-projects-books` 生成 evidence。

## Implementation record

- Alembic 与 SQLAlchemy 已增加项目、项目文章关联和读书笔记模型。
- 管理 API 已实现两种内容的草稿创建、列表、读取、乐观锁自动保存和显式发布；URL、阅读状态、评分与文章关联均在边界验证。
- 公开 API 只返回已发布内容，公开项目详情会再次过滤关联文章状态。
- Nuxt 已增加项目与读书笔记的管理列表、新建、编辑、实时 Markdown 预览、保存状态和发布动作，以及公开列表和固定 URL 详情页。
- 主导航和管理导航已接入项目与读书笔记。
- Pytest、Ruff、Vitest、Nuxt typecheck、生产构建、OpenAPI 生成与 Playwright 三内容闭环均通过。
- Spec 保留在 active 目录：仓库仍无 Git HEAD，无法满足 deterministic close 的历史前置条件。
