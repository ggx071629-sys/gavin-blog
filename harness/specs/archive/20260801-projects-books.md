---
id: archive-20260801-projects-books
level: L2
summary: 打通项目与读书笔记从草稿编辑、自动保存、发布到公开阅读的纵向闭环
load_when:
  - task:20260801-projects-books
author: Gavin
task_id: 20260801-projects-books
status: compressed
---

# 20260801-projects-books

Deterministic compressed record. The original active spec remains in Git history.

## Goal

单管理员可以创建、自动保存、预览并发布项目与读书笔记；公开读者可以通过 `/projects/{slug}` 和 `/books/{year}/{month}/{slug}` 浏览已发布内容，项目页展示已发布的关联文章。

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

## Result

Verified and closed by the harness close command.

## Evidence

[20260801-projects-books.json](../../verification/evidence/20260801-projects-books.json)

Closed at 2026-08-01T16:43:36.197827+00:00.
