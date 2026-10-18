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

## 当前功能模块与责任映射

以下表格是当前产品模块清单。压缩规格、历史 evidence、旧数据库迁移和兼容枚举只承担审计、升级或历史记录读取／显示兼容责任，不构成仍可使用的产品模块。

| ID | 模块 | Web 所有权 | API／数据所有权 | 长期边界 |
| --- | --- | --- | --- | --- |
| M01 | 公开阅读与导航 | 首页、文章、项目、读书、归档、关于页面及响应式站点壳层 | 已发布内容与公开上下文读取 | Web、API 与 Contracts README |
| M02 | 文章写作、发布与修订 | 管理文章列表、编辑、预览、发布、修订差异与回滚界面 | 工作副本、乐观锁、不可变发布修订、引用快照与回滚 | API README、OpenAPI |
| M03 | 栏目、标签与全站搜索 | 公开筛选、搜索页、管理分类界面 | taxonomy CRUD、FTS5 公开索引与稳定分页 | Web/API README、OpenAPI |
| M04 | 项目与读书笔记 | 公开列表／详情和管理编辑器 | 工作副本、发布修订、项目关联文章与书摘字段 | Web/API README、OpenAPI |
| M05 | 媒体与内容可移植性 | 媒体库、编辑器媒体字段、回收站与导入导出入口 | 媒体适配器、格式／资源校验、软删除恢复、Markdown ZIP 导出与多文件草稿导入 | API README、媒体与导入 ADR |
| M06 | 认证与个人资料 | 管理登录、账号安全与恢复、会话管理、Profile 与简历管理、公开名片 | Session、CSRF、验证码与恢复、凭据修改、Profile 可见性及版本化简历 | Web/API README、账号管理说明、OpenAPI |
| M07 | 内容发现输出 | canonical、Open Graph、结构化数据、RSS、站点地图与 robots | 只读公开投影和稳定内容 URL | Web README、产品基线 |
| M08 | 工程控制面 | 同源代理、质量与 E2E 客户端 | SQLite/Alembic、配置与测试隔离 | AGENTS、Harness 索引、发布准备 |
| M09 | 公开问答消费层（默认关闭） | 可用性驱动的「问 Gavin」入口、懒加载面板、同源 SSE、来源与简历附件 | 匿名 session／SSE、tombstone fence、公开 session view 与当前来源资格复核 | Web/API/Contracts README、[来源接入决策](../decisions/20260911-assistant-source-ingestion.md) |
| M10 | 问答运营控制面（默认关闭） | `/admin/assistant` 概览、独立试问、总预算编辑、同步状态与高级维护 | runtime gate、执行范围隔离、分类账本与共同总预算、index task/rebuild/finalize、紧急停止 | Web/API/Contracts README、[问答管理执行与预算决策](../decisions/20260910-assistant-management.md) |
| M11 | 关于页内容编辑与发布 | `/admin/about` 编辑器、草稿预览、版本历史与公开 About 投影 | About 内容单例、工作副本、乐观锁、不可变发布修订、回滚与助手来源资格 | Web/API README、OpenAPI |

`M01` 至 `M11` 是跨文档、测试合同和 evidence 使用的稳定模块 ID；模块名称或说明文字调整时不得顺带重编号。新增、拆分、合并或退役模块必须显式更新产品基线与模块验证合同，默认关闭不等于退役。

默认关闭的匿名公开问答现包含 API 内核、可选 Web 消费层与单管理员运营页。Web launcher flag、API capability、runtime gate 和 readiness 分属不同权威；运营页只聚合本地被动事实，不实时探活。一次问题可把同一短会话最近最多 4 个完整、未清理的成功问答 pair 作为明确分区的不可信历史发送给模型；历史 query/prompt 都只在节点内瞬时构造。普通公开关闭只撤销公开执行，后台试问按独立资格继续；紧急停止与索引切换撤销两种执行。撤销不能追回已越过 sending 的调用，但 epoch 阻止被撤销范围的正文、事件、history、checkpoint 与 publish，只允许无正文保守结算。About 默认 seed／静态模板不进入 RAG；显式合格的当前发布修订和当前有效简历已接入，草稿与失效版本排除。OpenAPI 路由或 dashboard healthy 也不等于真实供应商可用。生产资格状态唯一为 `LOCAL_READY → QUALIFICATION_GO_CANDIDATE | QUALIFICATION_NO_GO`；task close 只完成一次有真实目标证据的资格分类，不是最终 Go。只有新鲜 GO candidate 才能由管理员在任务外继续 `FINAL_GO → PUBLIC_ENABLED`。当前仍是 `LOCAL_READY` 与生产部署 No-Go。

## 写作与媒体

- 单管理员后台 Markdown 编辑器，支持草稿、预览、发布和自动保存。
- Markdown 支持 GFM、代码高亮、目录、脚注、提示块、Mermaid 和 KaTeX。
- 媒体支持拖拽或粘贴上传、WebP/AVIF 转换、外部链接，以及本地／对象存储抽象。
- 支持回收站与 Markdown 导入导出。

## 搜索、认证与隐私

- SQLite FTS5 全站搜索覆盖已发布文章、栏目、标签、项目和读书笔记。
- 服务端 Session、HttpOnly Cookie、CSRF 防护和登录限流；单管理员可管理用户名、密码、邮箱与登录会话，并通过验证码或恢复流程找回账号。具体配置与边界见 [账号管理说明](../../../apps/web/ACCOUNT-MANAGEMENT.md)。
- 无公开注册、评论、统计和站内联系表单。

## 技术与质量

- 前端：Nuxt、Vue、TypeScript、Tailwind CSS。
- 后端：Python、FastAPI、REST、OpenAPI。
- 数据：SQLite、SQLAlchemy 2.0、Alembic。
- 测试：Pytest、Vitest、Playwright。
- 目标：WCAG AA；桌面 Lighthouse 的 Performance、Accessibility、Best Practices 与 SEO 发布门槛均为 90。
- SEO：RSS、站点地图、规范链接、Open Graph 和结构化数据。
- 视觉：Electric Editorial 双主题技术刊物风格；字体与颜色的当前实现以 [全站样式](../../../apps/web/assets/css/main.css)、[写作台样式](../../../apps/web/assets/css/studio.css) 和 [Web 边界](../../../apps/web/README.md) 为准，写作台继承全站主题变量。公开站移动菜单是可访问 overlay dialog。

## 交付状态

下列阶段已经交付并通过对应规格验证，不再作为待建路线：

1. 核心文章闭环。
2. 完整内容系统：栏目与标签、项目与读书笔记、FTS5 全站搜索、媒体管线、回收站与 Markdown 导入导出。
3. 视觉与工程质量完善：公共体验、SEO 与内容发现、可重复质量门禁。
4. 媒体内联生命周期、文章公开引用、wikilink/反链和不可变文章修订等后续增量。

公开问答第四阶段的 runtime-integrity archive/evidence 按当时 Harness 契约形式关闭并保持历史原样；关闭后补救仍归第四阶段且不追溯改写原证据。第五阶段交付默认关闭的管理员启停、被动健康、索引队列/重建/finalize 和三类费用控制面；它不是 production Go。其后已完成本机真实 E5／Chat 联调、第二版管理试问与总预算、账号管理及 About／简历来源接入。各次验收只证明对应版本与环境，记录见 [实施计划与验收资料](../../../plan-build/README.md) 和 [问答管理决策](../decisions/20260910-assistant-management.md)。真实生产供应商合同、最终代理链、备份恢复与目标主机资格仍需独立验收。

本地开发不强制 Docker，使用 Node.js、Python 虚拟环境和本地 SQLite。生产平台仍未由管理员选定；资格 spec 明确禁止在选择前用通用 Docker／systemd／Windows 占位资产冒充交付。当前结论仍是本地发布候选可验证、公开问答 `LOCAL_READY`、生产部署 No-Go。
