---
id: spec-20260801-content-taxonomy
level: L1
summary: 为文章增加栏目与标签管理、关联和公开筛选，启动完整内容系统阶段
load_when:
  - task:20260801-content-taxonomy
author: Gavin
task_id: 20260801-content-taxonomy
status: verified
---

# Content taxonomy

## Context

核心文章闭环已经实现。产品基线的第二阶段是“完整内容系统”，其依赖顺序为：栏目与标签、项目与读书笔记、FTS5 搜索、媒体管线、回收站与导入导出。本任务交付第一个可独立验证的纵向增量，为后续内容类型和搜索建立稳定的组织边界。

## Goal

单管理员可以维护栏目与标签并关联到文章；公开读者可以看到文章的栏目与标签，并在文章列表按栏目或标签筛选已发布内容。

## Non-goals

- 项目、读书笔记及文章与项目的关联。
- FTS5 全站搜索。
- 媒体上传、格式转换和存储适配器。
- 回收站、Markdown 导入导出。
- 栏目层级、标签别名、拖拽排序与批量编辑。

## Acceptance criteria

- Alembic 新增栏目、标签、文章标签关联及文章可选栏目外键；栏目和标签 slug 唯一。
- 管理 API 支持栏目与标签的读取、创建、更新和删除；仍受 Session 与 CSRF 保护。
- 文章创建与带版本号自动保存可以设置一个栏目和多个标签；无效关联返回 `422`，并保留 `409` 乐观锁语义。
- 已使用的栏目或标签不能被删除，API 明确返回 `409`。
- 公开文章响应包含栏目与标签；公开列表支持 `category` 和 `tag` slug 查询参数，且永不返回草稿。
- Nuxt 管理端提供栏目与标签维护入口，并在文章编辑器中支持元数据关联。
- 公开文章卡片和详情展示栏目与标签；文章列表提供可分享 URL 的栏目／标签筛选。
- Pytest 覆盖 CRUD、防护、关联、删除冲突、筛选与草稿隔离；Vitest 覆盖筛选查询工具。
- OpenAPI 快照与前端 TypeScript 契约同步。

## Risks

- 关联表更新可能产生重复或悬空引用，因此数据库使用唯一约束与外键，API 在提交前验证全部 ID。
- 删除分类元数据可能破坏已发布文章，因此已被引用时拒绝删除。
- 自动保存元数据仍需服从文章版本号，避免正文与分类信息互相覆盖。
- 公开筛选可能泄漏草稿关联，因此所有查询先约束 `published` 状态。

## Verification plan

- 在隔离 SQLite 数据库执行 Alembic 到最新版本并检查迁移链。
- Pytest 执行现有核心闭环和新增 taxonomy 集成测试。
- Vitest 验证公开筛选查询参数生成。
- Ruff、Nuxt typecheck 与生产构建通过。
- 重新生成 OpenAPI 快照并确认工作区无契约漂移。
- 运行 `python -m tools.harness index` 与 `python -m tools.harness verify 20260801-content-taxonomy` 生成紧凑 evidence。

## Implementation record

- 新增栏目、标签、文章栏目外键与文章标签关联的 Alembic 迁移和 SQLAlchemy 模型。
- 管理 API 已实现 taxonomy CRUD、Session／CSRF 防护、引用删除冲突与文章乐观锁关联更新。
- 公开 API 已返回栏目和标签并支持按 slug 筛选，taxonomy 计数只统计已发布文章。
- Nuxt 已实现栏目与标签维护、文章元数据编辑、公开展示与可分享 URL 筛选。
- Pytest、Ruff、Vitest、Nuxt typecheck、生产构建、OpenAPI 生成和 Playwright 用户闭环均通过。
- Spec 保留在 active 目录：仓库仍无 Git HEAD，无法满足 deterministic close 的历史前置条件。
