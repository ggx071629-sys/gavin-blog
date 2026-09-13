---
id: web-boundary
level: L1
summary: Nuxt Web 应用的责任边界与当前本地 MVP 实现
load_when:
  - frontend
  - user-interface
author: Gavin
---

# Web boundary

本目录是博客前端，使用 Nuxt、Vue、TypeScript 和 Tailwind CSS，负责公开阅读页面、单管理员写作台及问答界面。业务规则、认证、数据库和模型调用由 [API](../api/README.md) 拥有；接口定义与生成流程见 [Contracts](../../packages/contracts/README.md)。本文描述当前代码，历史设计与阶段验收见 [plan-build](../../plan-build/README.md)。

## 代码结构

| 路径 | 职责 |
| --- | --- |
| [pages/](pages/) | 首页、文章、读书、项目、归档、搜索、关于页及 `admin/` 管理路由 |
| [components/](components/) | 阅读模板、内容编辑器、导航、个人名片、公开助手与管理试问组件 |
| [composables/](composables/) | API 请求、公开资料、自动保存、助手可用性与共享浮层状态 |
| [layouts/](layouts/) / [middleware/](middleware/) | 公共与后台外壳、管理员路由守卫 |
| [server/](server/) | 同源 API 代理、安全响应头、RSS、站点地图和 robots |
| [assets/css/](assets/css/) / [public/](public/) | 主题与页面样式、静态资源；[Studio 资源说明](public/studio/README.md) |
| [types/](types/) / [utils/](utils/) | API 消费类型、Markdown、内容、分页与问答协议校验 |
| [tests/](tests/) / [scripts/](scripts/) | 单元、E2E、生产质量、失败态测试及执行工具 |
| [nuxt.config.ts](nuxt.config.ts) / [package.json](package.json) | Nuxt 配置、依赖和 Web 命令 |

数据库和上传媒体不由 Web 管理；`.nuxt/`、`.output/` 是生成目录，不能当作业务源码或持久化数据。

## 页面与内容边界

公开助手成功回答提供“有帮助/没有帮助”选择，再次点击撤销；请求只发送选择，不附带问答正文。按钮在提交中禁用，确认前不改变已选状态；10秒未确认显示待核查提示，清除/换会话后忽略迟到结果。数据说明告知反馈随原回答TTL或清除删除且不续期。恢复解析只接受 helpful/unhelpful/null，旧无反馈快照保持可读；过期或非回答不能附带反馈。管理概览仅展示当前有效赞踩和当天阶段耗时，对错误计数提供人工核查提示，不把赞踩称为正确率或发送外部告警。

公开路由为 `/`、`/articles`、`/notes/{year}/{month}/{slug}`、`/books` 及其年月详情、`/projects` 及其 slug 详情、`/archive`、`/search`、`/about`。管理员页面位于 `/admin`，包括登录与找回密码、文章/读书/项目、关于页、个人名片、栏目标签、媒体、内容迁移、问答运营与账号安全。

首页由 [HomeNotebookHero](components/HomeNotebookHero.vue)、[HomeAtlas](components/HomeAtlas.vue) 和 [ProfileCard](components/ProfileCard.vue) 组成，最近更新读取有界的真实文章集合；图谱失败与空站分开处理。公开导航由 [SiteHeader](components/SiteHeader.vue)、[SiteNavIcon](components/SiteNavIcon.vue) 和 [SiteFooter](components/SiteFooter.vue) 维护。当前布局以页面模板和样式为准，不把旧阶段的侧栏、行列表、卡片尺寸或截图当成现行约束。

文章、项目和读书编辑共用 [WritingWorkspace](components/WritingWorkspace.vue) 及自动保存逻辑。自动保存只更新工作副本；预览、站内离页和发布先等待最新保存成功，冲突或失败阻止后续动作并保留输入。发布使用最新版本并明确确认，公开页面只读取后端发布快照。新建失败、未保存引用、媒体 Alt 校验和浏览器离页提醒仍分别处理；取消草稿不会自动删除共享媒体。

文章与关于页提供版本历史、差异和确认回滚；当前没有项目或读书的独立版本历史页面。三类后台列表通过服务端 `/admin/{articles,books,projects}/query` 搜索、筛选、计数与分页；当前页未发布修改数量不代表全站数量。媒体使用加载更多、去重、软删除与恢复；内容工具提供回收站及 Markdown ZIP 导入/导出，导入只创建草稿。

公开阅读共用 [ReadingLayout](components/ReadingLayout.vue) 和 [MarkdownArticle](components/MarkdownArticle.vue)，包括 GFM、目录、代码复制、Mermaid、KaTeX、引用与反链。正文标题与页面唯一 H1、锚点和目录保持一致；图表/公式按需加载，宽代码和表格局部滚动。canonical、Open Graph、JSON-LD、RSS 和站点地图使用公开内容；搜索结果页为 noindex。未显式写摘要时从 Markdown 提取纯文本。

公开空数组、明确 404、上游错误分别呈现。认证仅在明确 401 时转登录；注销未确认时不假称已退出。分页参数由 API 上限约束，非法页码规范化，搜索分页保留关键词。

栏目与标签操作由 `TaxonomyManager` 使用局部 15 秒等待预算；保存、删除或核对列表超时后退出等待并保留输入。超时只表示客户端未确认结果，不表示服务器未写入或已回滚。界面提供“核对最新列表”的只读操作，核对后保留输入供人工判断，不自动重放 POST/PATCH/DELETE；离开页面中止本组件等待。该预算不应用到全站请求，也不改变后端写入协调或数据库事务。

## 关于页与个人名片

`/about` 同时读取 `/api/v1/about-page` 的当前发布内容和 `/api/v1/profile` 的公开身份资料。关于页工作副本、预览、发布与修订由 `/admin/about` 管理；`statement` 与 `profile.bio` 独立，能力领域和近期动态各最多十项。

[AboutPublicBody](components/AboutPublicBody.vue) 展示身份卡、已发布自述 `statement`、写作主题 `editorial_topics`、能力、近期动态、本站说明与联系渠道；自述和主题按纯文本渲染。公开页只读取发布版，后台预览可展示工作副本。问答仍只接纳主动发布且具备资格的字段。

`/admin/profile` 管理身份、头像、技能、渠道和公开字段可见性。简历首次保存或换址自动入队，同址替换 PDF 后显式刷新；有未保存地址时禁止刷新，活动任务只轮询只读状态，隐藏/离页停止。内容和数据状态由 API 判定，不通过读取 Web 源码生成资料。

账号改密、恢复、邮件状态和会话撤销已实现，详见 [账号页面](ACCOUNT-MANAGEMENT.md)。

## API 与类型边界

浏览器只使用同源 `/api/v1`；[代理](server/routes/api/v1/[...path].ts) 读取私有 `NUXT_API_UPSTREAM` 转发到 API。`NUXT_PUBLIC_API_BASE` 是配置覆盖项，当前支持边界仍是同源相对基址。站点公开地址由 `NUXT_PUBLIC_SITE_URL` 配置；模型、SMTP、数据库和 HMAC 密钥不得进入 public runtime config。

问答代理对白名单路径执行严格 URL 与身份校验、禁止重定向并逐段转发 SSE。范围包括匿名 availability/sessions/session/questions、管理 trial 路由；当前有效简历 PDF 的精确无查询 GET 走独立附件分支，不创建问答会话。浏览器不直连模型、Worker、SQLite 或 Qdrant。

[types/api.ts](types/api.ts) 仍维护存量手写消费模型；[types/account.ts](types/account.ts) 和 [types/resume.ts](types/resume.ts) 已直接引用 Contracts 生成的 schema。接口变化需检查实际消费者与运行时 parser，不能只生成 OpenAPI 就认定跨端同步完成。

Nitro [安全中间件](server/middleware/security-headers.ts) 提供防框架、nosniff、Referrer/Permissions Policy 与 CSP Report-Only；HSTS 和最终 SSE 链需在真实 HTTPS 边缘验证。当前代码与本地验收不表示已经获得生产公开资格。

## 公开问答与管理试问

`NUXT_PUBLIC_ASSISTANT_UI_ENABLED` 默认关闭。启用后，公共布局通过 [useAssistantAvailability](composables/useAssistantAvailability.ts) 在挂载、路由变化和可见性变化时读取 `/assistant/availability`，可见期间定时刷新；失败视为不可用。入口同时要求可用性、Web 开关和允许的公开路径，因此“点击前完全不请求助手 API”不成立；创建会话和加载问答面板仍在用户打开之后。

顶部入口与 [AssistantLauncher](components/AssistantLauncher.vue) 共用 [AssistantHost](components/AssistantHost.vue)、[AssistantPanel](components/AssistantPanel.vue) 和单一 overlay owner。GSAP 悬浮球按需加载；减少动态效果、隐藏页面、面板/导航打开时暂停或清理。位置、引导与暂停偏好可保存在 localStorage，问题、回答与幂等材料不持久化到浏览器存储。

面板按视口使用桌面非模态浮窗、平板抽屉或手机全屏；导航与问答不能同时占有模态焦点和滚动锁。IME 选词不发送，手机 Enter 换行；等待、拒答、传输错误、输入预算不足、结果未确认和删除未确认保留各自状态。恢复、SSE、轮询与清除共用 generation 防止迟到结果复活；检查已有结果不自动重问，停止接收不等于取消后端执行或费用。

引用与来源经过相同的严格校验，恢复结果也不能绕过。允许路径见 [allowlist.ts](utils/assistant/allowlist.ts)，包括已发布文章/项目/读书、个人资料首页、精确 `/about` 和版本化简历附件；未知别名、非法路径或不一致来源使回答隐藏。多个引用编号可指向同一来源，但每个编号分别显示服务端章节或 PDF 页码，点击编号聚焦对应定位卡并可返回原编号。没有章节时提示在来源正文核查；链接仍打开来源页面或下载该版 PDF，不承诺自动定位原句，不展示模型 supports。

`/admin/assistant` 已包含可用性概览、费用与总预算、分页同步任务、独立试问和高级维护。预算修改受后端版本与部署授权上限约束；紧急停止、重试、重建和 finalize 保留确认及错误反馈。管理试问与匿名会话分离；页面刷新只读状态，不触发模型探测。当前维护入口可编辑运营预算，但不编辑供应商身份、模型价格或任意部署上限。

## 开发与验证

以下命令从仓库根目录执行，完整环境前提见 [项目说明](../../README.md) 和 [API 本机真实问答](../api/README.md#本机真实问答阶段-f)。

| 命令 | 用途 |
| --- | --- |
| `npm run dev:web` | 普通 Web 开发；助手入口默认关闭 |
| `npm run dev:assistant` | development 离线问答；临时 runtime、确定性 test provider |
| `npm run dev:assistant:real` | development 真实 E5/Qdrant/Chat；持久 runtime 与已验证配置 |
| `npm run build:web` | Web 生产构建 |
| `npm run test:web` | Vitest 单元测试 |
| `npm run test:e2e` | 核心通过后运行助手专用 Playwright 套件 |
| `npm run quality:web` | 类型、lint、单元、构建、生产质量及失败态检查 |

两种问答开发入口都不授权生产公开启用。E2E 使用隔离 API/媒体数据和受控供应商；当前核心与助手端口、环境清理和进程管理以 [执行脚本](scripts/run-playwright-e2e.mjs) 及各 `playwright*.config.ts` 为准。运行命令不等于验收已经通过，结果应引用对应证据。

## 文档维护

访客清除对话在服务端返回204或202后清空本地正文；拒绝或网络中断时保留当前可见记录，明确提示清除未确认并禁止继续提问，直到显式清除或重新核对会话。请求代次仍阻止迟到回答恢复正文。隔离助手 E2E 使用默认 `.nuxt` 输出匹配静态 tsconfig，并显式启用离线说明标志；该标志必须与后端测试供应商匹配。费用身份明细来自已有 scope 账本，无对应账本行时不虚构身份费用；没有耗时样本时显示未确认，不能当作零耗时。

路由、组件归属和用户行为改变时更新本文；账号流程更新 [ACCOUNT-MANAGEMENT.md](ACCOUNT-MANAGEMENT.md)，Studio 资源与主题边界更新 [资源说明](public/studio/README.md)。接口字段变更同时检查 API、Contracts、消费类型与 parser。阶段过程和历史测量归入 [plan-build](../../plan-build/README.md)，不继续追加到当前边界说明中。[UI-FOUNDATION.md](UI-FOUNDATION.md) 是第一阶段历史记录，不能代替当前样式与测试配置。

问答正文中的数组下标由 API 用行内反引号标界；引用解析只忽略此边界内的数组标记，并保留旧版未标界引用。公开面板和管理试问以文本插值显示数组，移除数组的显示边界，真实引用仍校验允许路径及来源闭合；恢复结果沿用同一解析器。不启用 Markdown 或 HTML 执行。

有限多轮：只从上一条仍在TTL内的成功回答中取唯一公开来源位置，复核当前发布投影再检索；来源名称只帮助确定对象，旧问题/答案正文不进入新提示。对象缺失、多来源、条目序号或失效时返回 `clarification_required`；界面显示“需要明确对象”，刷新可恢复，明确对象后可继续。独立问题不拼接旧问题。最多四轮及原TTL保留；任意自然语言指代和答案条目映射仍未支持，实际多轮质量待Q5。

页面优先只在问题明确指向当前页（例如“这篇文章”“this page”）或成功解析唯一来源时启用。可识别的全站完整清单/总数和全局最新/当前任职请求分别返回 `completeness_unverified` 与 `freshness_unverified`，在模型前停止；界面明确“完整性尚未核验”或“时效尚未核验”。普通局部清单、教程技术计数和限定的历史事实仍走证据问答。规则覆盖有限，未建立全量库存、事实时效证明、通用重排或任意长文完整性，片段不得冒充全文。
