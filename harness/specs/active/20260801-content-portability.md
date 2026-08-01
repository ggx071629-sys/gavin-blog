---
id: spec-20260801-content-portability
level: L1
summary: 为三类内容提供安全回收站及可往返的 Markdown 导入导出
load_when:
  - task:20260801-content-portability
author: Gavin
task_id: 20260801-content-portability
status: verified
---

# Content portability

## Context

第二阶段的最后一项要求是回收站与 Markdown 导入导出。现有三类内容没有删除语义，内容也无法以仓库外的可读格式备份或迁移。

## Goal

管理员可以软删除、查看和恢复文章、项目、读书笔记；可以把全部内容导出为 Markdown ZIP，并把受支持的 Markdown 文件导入为草稿。

## Non-goals

- 定时清空、保留策略、版本历史和跨站增量同步。
- 导入任意 YAML 方言、附件打包或媒体 URL 下载。
- 导入时自动发布内容。

## Acceptance criteria

- Alembic 为文章、项目和读书笔记增加 `deleted_at`，现有数据保持未删除。
- 三类管理 API 提供软删除；统一回收站 API 支持列表、恢复和显式永久删除，所有变更受 Session/CSRF 保护。
- 管理常规列表、公开读取与 FTS5 搜索排除回收站内容；恢复后原发布状态与公开路径可重新访问。
- 导出 API 生成 ZIP，每条内容一个 UTF-8 Markdown 文件，front matter 保存类型、slug、状态及类型特有元数据。
- 导入 API 验证大小、UTF-8、front matter、类型和 slug；成功内容始终创建为草稿，slug 冲突返回 `409`，批次结果可观察。
- Nuxt 提供内容工具页用于回收站、恢复、永久删除、Markdown 导入和 ZIP 导出，并加入管理导航。
- Pytest 覆盖三类软删除隔离、恢复/永久删除、导出内容与导入验证；OpenAPI 与 TypeScript 契约同步。

## Risks

- 永久删除不可恢复，因此 UI 和 API 都要求明确的二次确认语义。
- 导入文件不可信，因此限制文件数、单文件大小、路径与 front matter 字段，不解析任意对象。
- 项目关联和文章分类可能在目标站点不存在，因此导出使用稳定 slug，导入只关联已存在对象并报告缺失项。

## Verification plan

- Alembic 迁移空库并检查三列默认语义。
- Pytest 覆盖回收站、公开隔离和 Markdown ZIP 往返。
- Vitest、Nuxt typecheck、生产构建与 Playwright 内容工具闭环通过。
- 重新生成 OpenAPI 并运行 Harness verify。

## Implementation record

- Alembic 为文章、项目和读书笔记增加 `deleted_at`；管理列表、公开读取、分类计数、项目关联和 FTS5 均执行回收站隔离。
- 三类管理 API 提供软删除，统一内容工具 API 提供列表、恢复和受 CSRF 保护的永久删除。
- 导出生成每项一份 UTF-8 Markdown 的 ZIP，使用安全、可读的 YAML front matter；导入使用 `safe_load`、批次大小/数量/slug 校验并始终创建草稿。
- Nuxt 管理列表已接入删除动作，内容工具页支持恢复、二次确认永久删除、ZIP 下载和多文件导入。
- Pytest 三类回收站与导入导出测试及 Playwright 下载/导入/恢复闭环通过。
