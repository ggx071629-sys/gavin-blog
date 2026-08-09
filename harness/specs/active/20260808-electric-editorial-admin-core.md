---
id: spec-20260808-electric-editorial-admin-core
level: L1
summary: 以 Electric Editorial 共享令牌重构非孵化管理后台，并保留全部认证与内容工作流
load_when:
  - task:20260808-electric-editorial-admin-core
author: Gavin
task_id: 20260808-electric-editorial-admin-core
status: active
---

# Context

前两阶段已经完成公开博客的 Electric Editorial 双主题令牌、公共壳层和全部公开页面。非孵化管理后台仍混用旧的 slate／blue／purple Tailwind 样式、固定深色登录页、横向单行导航和重复的圆角卡片，尚未形成适合内容运营的高密度界面。

`web_prototype/` 共包含 17 个公开站点 Stitch 页面，没有登录、后台、CMS、编辑器或数据管理原型。因此本阶段不能声称逐像素复刻后台原型。后台视觉必须明确标记为派生设计：继承浅色／深色 Stitch 设计系统和现有 `--ee-*` 语义令牌，以当前路由、真实字段和既有行为为事实来源，并按“公开博客重阅读与品牌，管理后台重信息密度与操作效率”的产品边界组织界面。

设计判读固定为：面向单一站点管理员的内容生产与运营后台，使用 Electric Editorial 品牌语言，`variance=3`、`motion=2`、`density=8`。本地 UI 数据库给出的 Bento 营销布局、超大标题、Fira／Libre Bodoni 字体和新配色与现有后台任务及 Stitch 令牌冲突，明确不采用；仅采用键盘顺序、跳到正文、焦点、表单反馈、移动端表格处理和双主题对比度等通用 UX 规则。不新增 UI 框架、字体或动效依赖。

原型、路由与现有页面文件对应如下：

| 原型依据 | 路由 | 现有页面文件 | 状态 |
| --- | --- | --- | --- |
| 无后台原型；由双主题令牌与认证行为派生 | `/admin/login` | `apps/web/pages/admin/login.vue` | 当前固定深色玻璃卡片；需双主题、键盘和错误态验收 |
| 无后台原型；由高密度内容列表模式派生 | `/admin/articles` | `apps/web/pages/admin/articles/index.vue` | 保留状态、版本、发布修订、未发布修改、预览、编辑、删除和分页 |
| 无后台原型；由统一创建表单模式派生 | `/admin/articles/new` | `apps/web/pages/admin/articles/new.vue` | 保留字段顺序、slug 同步、栏目标签和创建跳转 |
| 无后台原型；由编辑工作台模式派生 | `/admin/articles/:id/edit` | `apps/web/pages/admin/articles/[id]/edit.vue`、`apps/web/components/ArticleEditor.vue` | 保留自动保存队列、冲突、预览、版本历史和发布屏障 |
| 公开详情原型只提供阅读层参考 | `/admin/articles/:id/preview` | `apps/web/pages/admin/articles/[id]/preview.vue` | 保留草稿告警、真实 Markdown 和返回编辑；不能冒充公开已发布状态 |
| 无后台原型；由版本审计模式派生 | `/admin/articles/:id/revisions` | `apps/web/pages/admin/articles/[id]/revisions.vue` | 保留分页、详情、差异、来源链、回滚确认和全部测试钩子 |
| 无后台原型；由高密度内容列表模式派生 | `/admin/projects` | `apps/web/pages/admin/projects/index.vue` | 保留状态、版本、编辑、删除和分页 |
| 无后台原型；由统一创建表单模式派生 | `/admin/projects/new` | `apps/web/pages/admin/projects/new.vue` | 保留 URL、关联文章、Markdown 和创建跳转 |
| 无后台原型；由编辑工作台模式派生 | `/admin/projects/:id/edit` | `apps/web/pages/admin/projects/[id]/edit.vue`、`apps/web/components/ProjectEditor.vue` | 保留关联文章、媒体、自动保存、冲突和发布 |
| 无后台原型；由高密度内容列表模式派生 | `/admin/books` | `apps/web/pages/admin/books/index.vue` | 保留阅读状态、版本、编辑、删除和分页 |
| 无后台原型；由统一创建表单模式派生 | `/admin/books/new` | `apps/web/pages/admin/books/new.vue` | 保留书籍元数据、Markdown 和创建跳转 |
| 无后台原型；由编辑工作台模式派生 | `/admin/books/:id/edit` | `apps/web/pages/admin/books/[id]/edit.vue`、`apps/web/components/BookNoteEditor.vue` | 保留封面选择、阅读状态、自动保存、冲突和发布 |
| 无后台原型；由双栏维护工具模式派生 | `/admin/taxonomy` | `apps/web/pages/admin/taxonomy.vue`、`apps/web/components/TaxonomyManager.vue` | 保留栏目／标签 CRUD、slug 同步、引用保护和错误反馈 |
| 无后台原型；由媒体资产工作台模式派生 | `/admin/media` | `apps/web/pages/admin/media.vue`、`apps/web/components/MediaUploader.vue` | 保留拖放、粘贴、文件选择、外链登记、复制和加载更多 |
| 无后台原型；由危险操作与迁移工具模式派生 | `/admin/content` | `apps/web/pages/admin/content.vue` | 保留导入、导出、恢复、永久删除、分页和确认语义 |
| 无后台原型；由设置与实时预览模式派生 | `/admin/profile` | `apps/web/pages/admin/profile.vue` | 保留字段、技能排序、媒体头像、公开性开关、版本冲突、离开提醒和首页预览 |

现有 `apps/web/layouts/admin.vue` 同时承载非孵化后台与 `/admin/incubator/**`。为满足孵化隔离，本阶段优先新增非孵化专用 `admin-core` 布局并切换上表适用页面；现有 `admin.vue`、`IncubatorShell.vue`、`IncubatorChainNav.vue` 和所有 `pages/admin/incubator/**` 保持不变。登录页继续使用无布局模式；文章草稿预览可使用独立预览模式，但 URL、认证中间件和返回路径不得改变。

# Goal

在不改变 API 契约、数据库、公开 URL、后台 URL、认证规则、内容状态机和自动保存／发布一致性屏障的前提下，完成 16 个非孵化后台路由的 Electric Editorial 双主题 UI 重构，建立高密度、可扫描、移动可用且满足 WCAG AA 的后台壳层、列表、表单、编辑器、版本历史和工具页面。

# Non-goals

- 不修改 `apps/api/`、数据库模型、Alembic、`packages/contracts/`、Cookie／CSRF／Session 规则或认证中间件。
- 不改变任何公开或管理 URL，不更改导航目标、表单字段名、字段顺序、测试选择器、API 请求体或业务状态值。
- 不新增筛选、搜索、批量选择、批量发布、统计指标、仪表盘或其他现有 API／状态机不支持的功能。
- 不修改 `apps/web/pages/admin/incubator/**`、`IncubatorShell.vue`、`IncubatorChainNav.vue` 或知识孵化专属组件、API、类型与状态。
- 不让孵化前的通用后台组件依赖知识孵化类型、API、状态或页面组件。
- 不重新设计已完成的公开页面；共享令牌或基础组件变化必须通过公开页面回归验证。
- 不引入 Fluent、Carbon、Material、shadcn、GSAP、图标库、新字体或其他新的 UI／动效依赖。
- 不硬编码虚构指标、内容、图片或示例用户；所有页面继续使用真实 API 数据。
- 不修改、移动或删除 `my_blog_fork/`，不建立共享依赖、submodule、符号链接或远程 UI 包。
- 不修改、解冻、关闭或继续实现 `20260807-github-discovery-ingestion` 与 `20260807-github-source-crawler`。
- 不恢复或合并 `codex/frozen-github-ingestion-checkpoint`，不提交或推送。

# Acceptance criteria

- 新的非孵化后台壳层在桌面采用紧凑侧边导航与实用工具区，在移动端收敛为可键盘操作的抽屉／菜单；保留文章、读书、项目、个人名片、栏目与标签、媒体、回收站与迁移、知识孵化、查看站点和退出的现有目标，并提供当前项语义、跳到正文和明确焦点。
- 后台壳层与登录页支持浅色／深色独立设计，复用 `--ee-*` 基础令牌；深色不是简单反转，浅色酸性绿不用于未达到 4.5:1 的小号文字。状态、错误、警告和成功不只依赖颜色表达。
- 登录页保留用户名、密码、CSRF 获取、限流错误、错误凭据反馈、hydration 禁用和登录后跳转；两种主题均满足 WCAG AA，密码管理器所需 autocomplete 不回归。
- 文章、项目和读书列表使用同一高密度列表语法，保留真实状态、版本和现有操作；桌面易扫描，390px 下重排为单列操作区且整页无水平溢出。不得为了视觉效果新增不存在的筛选、数据列或统计。
- 三类新建页复用统一页面标题、表单区、帮助／错误反馈和操作栏，保留现有字段顺序、输入类型、最大长度、slug 同步、默认 Markdown、关联数据与成功跳转。
- `ArticleEditor`、`ProjectEditor`、`BookNoteEditor` 建立一致的编辑工作台：桌面双栏呈现编辑与真实预览，移动端提供单列且可到达的编辑／预览顺序；自动保存状态、冲突警告、媒体插入、发布按钮、禁用条件和 `queue.flush()` 发布屏障保持原行为。
- 文章草稿预览明确展示“未公开”状态并保留返回编辑；渲染继续使用真实 `MarkdownArticle`，视觉上与公开阅读层同源但不能混淆为已发布页面。
- 版本历史页保留发布修订分页、当前修订、孵化来源链、快照详情、差异、回滚资格、确认和错误／成功状态；长 Markdown 与 diff 在桌面和移动端均可读，不造成页面级水平溢出。
- 栏目／标签、媒体、回收站与迁移、个人名片四类工具页分别形成一致的表单、资产、危险操作和设置预览模式；原有 CRUD、上传、复制、导入导出、恢复／永久删除、技能排序、公开开关、冲突与未保存离开提醒全部保留。
- 后台共用组件和样式使用语义类或语义令牌替代页面散落的 slate／blue／purple 与不一致圆角；公开博客和后台共享基础令牌，但后台不得直接复用只适合阅读的页面结构，也不得建立孵化依赖。
- 正文／表单文字在两种主题满足 WCAG AA；所有核心操作可由键盘完成，焦点顺序与视觉顺序一致，焦点环清晰，表单具备可见标签和就近错误，触控目标至少 44×44px，并尊重 `prefers-reduced-motion`。
- 16 个非孵化路由均执行 light/dark × 1440×1100/390×844 四象限的无溢出与视觉检查；每个页面族至少一个固定数据代表页执行 axe WCAG 2.0/2.1 A/AA，自动扫描零违规。
- `/admin/incubator`、`/admin/incubator/inbox` 和一个孵化详情页保留现有布局与可访问性基线；实现 diff 不得包含 `pages/admin/incubator/**` 或两个 Incubator 组件。
- 保留既有 `data-testid` 和高价值闭环；将依赖 `.editor-grid > div` 的脆弱测试定位改为稳定语义／testid 时，不改变可观察行为。
- Nuxt 类型检查、全部 Vitest、生产构建、适用 Playwright E2E、质量门禁、`git diff --check` 和 Harness 验证通过；首页 Lighthouse 四项继续不低于 90，后台页面维持 `noindex,nofollow`。

# Implementation slices

1. 后台基础与隔离：建立 `admin-core` 布局、后台语义样式／基础组件、双主题登录页，以及文章／项目／读书三个列表页；保留旧 `admin` 布局供孵化区使用。完成后项目必须可运行并通过登录与列表闭环。
2. 内容生产工作台：统一三类新建页、三类编辑器、文章草稿预览和版本历史；以现有自动保存、发布、预览、修订与回滚测试作为阻断门槛。
3. 内容运营工具：重构栏目与标签、媒体库、回收站与迁移、个人名片；保留复制、上传、导入导出、危险操作确认、版本冲突与离开提醒。
4. 全矩阵收敛：补齐后台四象限截图、axe、水平溢出、键盘／触控、公开页面和孵化隔离回归，修正所有对比度或响应式缺陷后再标记 verified。

# Risks

- Stitch 没有后台原型，任何后台布局都是有约束的派生而不是“严格复刻”；必须记录依据，不能把个人偏好或技能数据库误称为原型事实。
- UI 数据库两次把后台查询部分误路由为营销落地页；若机械采用会引入超大标题、Bento、滚动动画和新字体，破坏信息密度与现有品牌，因此只采用可验证的通用 UX 规则。
- `admin.vue` 被孵化页面共享；直接重构会越过阶段边界。新增 `admin-core` 布局会产生短期双后台壳层成本，但能保证冻结区不被意外重绘，后续只有在用户明确授权时才迁移孵化区。
- 编辑器、媒体库和版本差异包含宽内容；仅依赖 `overflow-x-auto` 可能掩盖整页溢出，必须区分局部代码／表格滚动与页面级溢出。
- 操作栏在窄屏容易把自动保存状态、预览、历史和发布挤压为不可用；需要按优先级重排，而不是缩小文字或触控目标。
- 全局 `.field`、按钮、状态和 Markdown 样式同时被公开页、后台和孵化区使用；修改前需确认消费者，必要时创建后台作用域类，避免公共页面或孵化基线回归。
- 原生 `confirm` 承载删除与永久删除确认。若更换为自定义对话框，必须完整处理焦点捕获、Esc、返回焦点、标签和异步状态；无法保证时保留原生确认，不为视觉统一牺牲安全语义。
- 64 个后台四象限视图会增加测试时间和截图数量；截图和重型报告只保存在本地，提交内容仅保留紧凑 evidence manifest。

# Verification plan

- TDD／组件：为新后台壳层、导航当前态、移动菜单、主题、状态标签、表单反馈和编辑工作台局部行为添加 Vitest；保持 autosave、profile、pagination、content 等现有测试通过。
- E2E：运行登录、文章／项目／读书创建-自动保存-预览-发布、分类、媒体上传、回收站恢复、Markdown 导入导出、个人名片、文章修订／回滚和分页闭环；保留所有现有 testid。
- Visual：使用隔离固定数据逐一访问 16 个非孵化路由，生成 light/dark × desktop/mobile 本地截图并进行人工检查；因无后台 Stitch 原型，验收比较派生设计规则、跨页一致性、层级、密度和状态完整性，不宣称像素级原型比对。
- Accessibility：Playwright + axe 对登录、列表、新建、三类编辑器、预览、版本历史、分类、媒体、内容工具和个人名片代表状态执行 WCAG 2.0／2.1 A/AA；额外检查跳到正文、菜单键盘操作、焦点返回、标题层级、44px 触控目标和状态非颜色依赖。
- Responsive：在 1440×1100、390×844 下检查全部非孵化路由页面级 `scrollWidth <= clientWidth`；Markdown 代码、diff 和必要的数据区域只允许组件内部受控滚动。
- Isolation：确认 `git diff --name-only -- apps/web/pages/admin/incubator apps/web/components/IncubatorShell.vue apps/web/components/IncubatorChainNav.vue my_blog_fork` 为空，并运行现有孵化代表页 axe／E2E 基线。
- Quality：从仓库标准入口运行 `npm run quality:web`，并补充适用的后台 Playwright 用例、`git diff --check` 与公开首页 Lighthouse 回归。
- Harness：在 `harness/` 生成索引并运行 `python -m tools.harness verify 20260808-electric-editorial-admin-core`；实现验证后提交紧凑 application／Harness evidence manifest，不提交截图、trace、Lighthouse 原始报告或其他重型产物。
