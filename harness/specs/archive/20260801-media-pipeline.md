---
id: archive-20260801-media-pipeline
level: L2
summary: 建立可迁移存储边界下的图片上传、转换、外链登记与编辑器插入闭环
load_when:
  - task:20260801-media-pipeline
author: Gavin
task_id: 20260801-media-pipeline
status: compressed
---

# 20260801-media-pipeline

Deterministic compressed record. The original active spec remains in Git history.

## Goal

管理员可以上传或登记图片，在媒体库查看稳定 URL，并把图片 Markdown 插入三类内容编辑器；当前使用本地适配器，未来可替换对象存储实现。

## Acceptance criteria

- Alembic 增加媒体资产表，记录来源、MIME、尺寸、alt 文本、稳定 URL 和派生格式。
- 配置外置媒体根目录、公开 URL 前缀、大小限制与允许格式；业务路由只依赖媒体存储协议。
- 管理 API 支持图片上传、外链登记和列表，所有变更受 Session/CSRF 保护。
- 上传验证 MIME、文件签名和大小，生成 WebP 与运行时支持的 AVIF 派生文件；文件名不可由用户控制。
- 公开媒体路由只服务已登记的本地派生文件，并防止路径穿越。
- Nuxt 媒体组件支持选择文件、拖放、粘贴、外链登记和 Markdown 插入，并接入文章、项目、读书笔记编辑器。
- Pytest 覆盖权限、验证、转换、存储和公开读取；OpenAPI 与 TypeScript 契约同步。

## Result

Verified and closed by the harness close command.

## Evidence

[20260801-media-pipeline.json](../../verification/evidence/20260801-media-pipeline.json)

Closed at 2026-08-01T16:43:07.288056+00:00.
