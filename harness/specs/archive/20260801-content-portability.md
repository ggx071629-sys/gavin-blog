---
id: archive-20260801-content-portability
level: L2
summary: 为三类内容提供安全回收站及可往返的 Markdown 导入导出
load_when:
  - task:20260801-content-portability
author: Gavin
task_id: 20260801-content-portability
status: compressed
---

# 20260801-content-portability

Deterministic compressed record. The original active spec remains in Git history.

## Goal

管理员可以软删除、查看和恢复文章、项目、读书笔记；可以把全部内容导出为 Markdown ZIP，并把受支持的 Markdown 文件导入为草稿。

## Acceptance criteria

- Alembic 为文章、项目和读书笔记增加 `deleted_at`，现有数据保持未删除。
- 三类管理 API 提供软删除；统一回收站 API 支持列表、恢复和显式永久删除，所有变更受 Session/CSRF 保护。
- 管理常规列表、公开读取与 FTS5 搜索排除回收站内容；恢复后原发布状态与公开路径可重新访问。
- 导出 API 生成 ZIP，每条内容一个 UTF-8 Markdown 文件，front matter 保存类型、slug、状态及类型特有元数据。
- 导入 API 验证大小、UTF-8、front matter、类型和 slug；成功内容始终创建为草稿，slug 冲突返回 `409`，批次结果可观察。
- Nuxt 提供内容工具页用于回收站、恢复、永久删除、Markdown 导入和 ZIP 导出，并加入管理导航。
- Pytest 覆盖三类软删除隔离、恢复/永久删除、导出内容与导入验证；OpenAPI 与 TypeScript 契约同步。

## Result

Verified and closed by the harness close command.

## Evidence

[20260801-content-portability.json](../../verification/evidence/20260801-content-portability.json)

Closed at 2026-08-01T16:42:26.383452+00:00.
