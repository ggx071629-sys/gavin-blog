---
id: product-brief
level: L1
summary: Gavin 个人技术博客的定位、能力范围、技术约束与开发顺序
load_when:
  - product-planning
  - feature-scope
  - content-model
author: Gavin
---

# 产品基线

## 定位

项目用于为未来的自己沉淀知识，同时作为求职与合作名片。品牌暂定 Gavin，后期允许更换独立博客名称。

## 内容与信息架构

- 内容：技术文章、问题排查、项目复盘、阶段总结、读书笔记。
- 组织：栏目与标签。
- 导航：首页、文章、读书笔记、项目、归档、关于、搜索；公开桌面与移动导航另有写作台入口，目标页受管理员认证保护。
- URL：`/notes/{year}/{month}/{slug}`、`/books/{year}/{month}/{slug}`、`/projects/{slug}`。
- 项目拥有独立详情页，并可关联相关文章。
- 已发布文章、项目和书摘通过正文 `[[wikilink]]` 与文章参考资料形成公开反链；草稿与未发布修改不进入公开关系。
- 读书笔记记录书籍、作者、封面、阅读状态、日期和评分。

## 写作与媒体

- 单管理员后台 Markdown 编辑器，支持草稿、预览、发布和自动保存。
- Markdown 支持 GFM、代码高亮、目录、脚注、提示块、Mermaid 和 KaTeX。
- 媒体支持拖拽或粘贴上传、WebP/AVIF 转换、外部链接，以及本地／对象存储抽象。
- 支持回收站与 Markdown 导入导出。

## 搜索、认证与隐私

- SQLite FTS5 全站搜索覆盖已发布文章、栏目、标签、项目和读书笔记。
- 服务端 Session、HttpOnly Cookie、CSRF 防护和登录限流。
- 无公开注册、评论、统计和站内联系表单。

## 技术与质量

- 前端：Nuxt、Vue、TypeScript、Tailwind CSS。
- 后端：Python、FastAPI、REST、OpenAPI。
- 数据：SQLite、SQLAlchemy 2.0、Alembic。
- 测试：Pytest、Vitest、Playwright。
- 目标：WCAG AA；桌面 Lighthouse 的 Performance、Accessibility、Best Practices 与 SEO 发布门槛均为 90。
- SEO：RSS、站点地图、规范链接、Open Graph 和结构化数据。
- 视觉：Electric Editorial 双主题技术刊物风格；中文标题与正文使用自托管 Noto Sans SC（400/700，设计 800 映射 700），拉丁使用 Inter，代码 JetBrains Mono。公开站移动菜单是可访问 overlay dialog。

## 交付状态

下列阶段已经交付并通过对应规格验证，不再作为待建路线：

1. 核心文章闭环。
2. 完整内容系统：栏目与标签、项目与读书笔记、FTS5 全站搜索、媒体管线、回收站与 Markdown 导入导出。
3. 视觉与工程质量完善：公共体验、SEO 与内容发现、可重复质量门禁。
4. 媒体内联生命周期、文章公开引用、wikilink/反链和不可变文章修订等后续增量。

知识孵化工作台曾完成首期实现，但已于 2026-08-26 从主产品退役；历史需求仅作归档参考，恢复该能力必须作为独立产品重新立项，不能重新耦合到博客发布链路。

本地开发不强制 Docker，使用 Node.js、Python 虚拟环境和本地 SQLite。部署暂不决定，只预留配置与存储迁移边界。当前结论仍是本地发布候选可验证，生产部署 No-Go。
