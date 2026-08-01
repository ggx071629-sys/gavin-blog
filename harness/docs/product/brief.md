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
- 导航：首页、文章、读书笔记、项目、归档、关于、搜索。
- URL：`/notes/{year}/{month}/{slug}`、`/books/{year}/{month}/{slug}`、`/projects/{slug}`。
- 项目拥有独立详情页，并可关联相关文章。
- 读书笔记记录书籍、作者、封面、阅读状态、日期和评分。

## 写作与媒体

- 单管理员后台 Markdown 编辑器，支持草稿、预览、发布和自动保存。
- Markdown 支持 GFM、代码高亮、目录、脚注、提示块、Mermaid 和 KaTeX。
- 媒体支持拖拽或粘贴上传、WebP/AVIF 转换、外部链接，以及本地／对象存储抽象。
- 支持回收站与 Markdown 导入导出。

## 搜索、认证与隐私

- SQLite FTS5 全站搜索覆盖文章、栏目、标签和项目。
- 服务端 Session、HttpOnly Cookie、CSRF 防护和登录限流。
- 无公开注册、评论、统计和站内联系表单。

## 技术与质量

- 前端：Nuxt、Vue、TypeScript、Tailwind CSS。
- 后端：Python、FastAPI、REST、OpenAPI。
- 数据：SQLite、SQLAlchemy 2.0、Alembic。
- 测试：Pytest、Vitest、Playwright。
- 目标：WCAG AA；Lighthouse 四项争取达到 90+。
- SEO：RSS、站点地图、规范链接、Open Graph 和结构化数据。
- 视觉：专业数字笔记／技术刊物风格，蓝色为主、紫色为辅，支持深浅主题。

## 交付顺序

1. 核心文章闭环。
2. 完整内容系统。
3. 视觉与工程质量完善。

完整内容系统按依赖顺序分为：栏目与标签、项目与读书笔记、FTS5 全站搜索、媒体管线、回收站与 Markdown 导入导出。每项均以可独立验证的纵向增量交付，不以一次性大改完成整个阶段。

第三阶段按风险和依赖拆分为：

1. 公共体验基线：响应式导航、主题、键盘与触屏可用性，并补齐归档和关于页面。
2. SEO 与内容发现：RSS、站点地图、规范链接、Open Graph 和结构化数据。
3. 质量门禁：类型、测试、构建、WCAG AA 与 Lighthouse 的可重复检查和明确阈值。

本地开发不强制 Docker，使用 Node.js、Python 虚拟环境和本地 SQLite。部署暂不决定，只预留配置与存储迁移边界。
