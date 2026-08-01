---
id: spec-20260801-media-pipeline
level: L1
summary: 建立可迁移存储边界下的图片上传、转换、外链登记与编辑器插入闭环
load_when:
  - task:20260801-media-pipeline
author: Gavin
task_id: 20260801-media-pipeline
status: verified
---

# Media pipeline

## Context

当前 Markdown 编辑器只能手写外部媒体 URL，读书封面也只能引用外链。产品边界要求支持拖放或粘贴上传、WebP/AVIF 转换、外链以及本地/对象存储抽象。

## Goal

管理员可以上传或登记图片，在媒体库查看稳定 URL，并把图片 Markdown 插入三类内容编辑器；当前使用本地适配器，未来可替换对象存储实现。

## Non-goals

- 视频、音频、PDF、在线裁剪和富媒体编辑。
- CDN、对象存储供应商实现与部署目录。
- 自动删除仍可能被 Markdown 引用的媒体。

## Acceptance criteria

- Alembic 增加媒体资产表，记录来源、MIME、尺寸、alt 文本、稳定 URL 和派生格式。
- 配置外置媒体根目录、公开 URL 前缀、大小限制与允许格式；业务路由只依赖媒体存储协议。
- 管理 API 支持图片上传、外链登记和列表，所有变更受 Session/CSRF 保护。
- 上传验证 MIME、文件签名和大小，生成 WebP 与运行时支持的 AVIF 派生文件；文件名不可由用户控制。
- 公开媒体路由只服务已登记的本地派生文件，并防止路径穿越。
- Nuxt 媒体组件支持选择文件、拖放、粘贴、外链登记和 Markdown 插入，并接入文章、项目、读书笔记编辑器。
- Pytest 覆盖权限、验证、转换、存储和公开读取；OpenAPI 与 TypeScript 契约同步。

## Risks

- 图片解码可消耗大量内存，因此同时限制请求字节数与像素数。
- 用户文件名和 MIME 不可信，因此用解码器识别格式并生成服务端随机键。
- AVIF 编码能力依赖 Pillow 构建；API 明确报告实际生成的派生格式，同时 WebP 为必需基线。

## Verification plan

- 迁移检查媒体表；用隔离临时目录执行真实上传与读取测试。
- Pytest 覆盖本地适配器、图片验证、认证与 CSRF。
- Vitest、Nuxt typecheck、生产构建与编辑器媒体 E2E 通过。
- 重新生成 OpenAPI 并运行 Harness verify。

## Implementation record

- Alembic 与 SQLAlchemy 增加媒体资产；FastAPI 路由依赖 `MediaStorage` 协议，当前应用注入本地适配器。
- 上传同时验证声明 MIME、图片签名、字节数和像素数，使用服务端随机键生成 WebP 与 AVIF；当前 Pillow 构建两种编码器均可用。
- 公开媒体按已登记资产和派生格式解析文件，不接受用户路径；外链只接受 HTTP(S)。
- Nuxt 媒体组件支持文件选择、拖放、粘贴、外链登记、Markdown 插入和封面 URL 选择，并接入三类编辑器和独立媒体库。
- Pytest 转换/权限/公开读取测试及 Playwright 真实上传闭环通过。
