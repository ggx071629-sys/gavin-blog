# 视觉改造第一阶段：基线与共用基础

> 历史记录：下文的尺寸、页面数量、断点、待办与测试结果属于 2026-09-05 的第一阶段，保留当时语境。当前页面和运行边界见 [Web README](README.md)，后台主题与静态资源见 [Studio 说明](public/studio/README.md)，后续阶段见 [plan-build](../../plan-build/README.md)。不得把本页旧样式或后续待办重新当作当前实现要求。

任务 `20260905-ui-foundation`；设计依据为本地 `plan-build/ui-improvement/design/PROPOSAL.md` 第一阶段。实施前版本 `917b16c03e36a528b6f0552bad7015fe7b6119c8`，规格先提交于 `3e6e71d`。本文件记录范围与实现；最终验收以 [Harness 规格索引](../../harness/specs/INDEX.md)及任务 evidence 为准。

## 改造前核对（2026-09-05）

- 源码事实：27 个 page 文件及独立 error 模板；公开、后台、无外壳登录及工作副本预览各有边界。既有设计截图位于本地 `plan-build/ui-improvement/design/evidence/original/`，是历史画面参考，不是本阶段测试结果。
- 颜色和字体已符合提案：浅色蓝、深色黄绿，Space Grotesk / Inter / Noto Sans SC / JetBrains Mono 均已自托管。无须更换依赖或字体。
- `body` 原来铺满点阵；公开桌面主题图标、手机字符图标、后台主题图标有重复实现；页尾直接写在 default layout。导航编号视觉权重偏高，手机无清晰的选中表面。后台侧栏宽 256px，组标题 10.4px。
- 现有公开导航为 <640px 全屏、640–1279px 抽屉、≥1280px 桌面；后台在 1024px 切换。均已有模态焦点与背景管理，不能照搬原型的普通展开菜单。公开链接提前关闭导致路由监听失去“从菜单导航”的信息，需要修复正文焦点。
- API、认证、工作副本与发布快照已有真实实现；原型中的内容图、模拟按钮和运营数据不能当成产品能力迁入。`plan-build/ui-improvement/UI_AUDIT_REPORT.md` 的既有用户修改不属于本阶段。

## 路由、组件与迁移边界

| 页面族 / 实际路径 | 共用组件 / 容器 | 本阶段与后续范围 |
| --- | --- | --- |
| `/` | default、SiteHeader、SiteFooter、ProfileCard、ArticleCard | 外壳与背景已改；作者构图、栏目图、内容取数留阶段 2 |
| `/articles` | PublicPageHero、PaginationNav、文章行列表 | 共用外壳；列表主布局留阶段 3 |
| `/notes/:year/:month/:slug` | MarkdownArticle、ContentToc、BacklinkList、阅读容器 | 命名原有 720px 阅读轴与 17px 正文；标题/目录/代码重排留阶段 3 |
| `/projects`、`/projects/:slug` | PublicPageHero、ProjectCard、MarkdownArticle、PaginationNav | 外壳；工程图和详情构图留阶段 3 |
| `/books`、`/books/:year/:month/:slug` | PublicPageHero、BookCard、MarkdownArticle、PaginationNav | 外壳；书目/封面/摘录布局留阶段 3 |
| `/archive`、`/about`、`/search` | PublicPageHero、分页、profile、搜索字段 | 外壳；各页内容轴留阶段 3 |
| error.vue（404 / 上游错误） | NuxtLayout、共用按钮 | 保留真实状态和返回入口；新断连图留阶段 3 |
| `/admin/login` | AdminThemeToggle → ThemeToggle、field、反馈样式 | 共享控件尺度；登录构图与业务合同保留，阶段 4 处理 |
| `/admin/articles`、`/admin/projects`、`/admin/books` | admin-core、AdminCoreNavigation、admin-list、PaginationNav | 紧凑框架与共用列表基础；页面工具与操作层级留阶段 4 |
| 上述三类 `/new` 与 `/:id/edit` | field、ArticleEditor / ProjectEditor / BookNoteEditor、MarkdownMediaField、MediaUploader | 共用表单尺度；自动保存、发布与设置区留阶段 4 |
| `/admin/articles/:id/preview`、`/:id/revisions` | 阅读模板 / admin-core、MarkdownArticle | 保留工作副本提示及版本逻辑；页面重排留阶段 4 |
| `/admin/profile`、`/admin/taxonomy`、`/admin/media`、`/admin/content`、`/admin/assistant` | admin-core、ProfileCard、TaxonomyManager、MediaUploader、AdminDialog | 共用框架与状态样式；各管理页重排留阶段 5 |
| 公开问答（非独立路由） | AssistantHost、AssistantPanel、usePublicOverlay | 保持默认关闭及单一 overlay owner；面板改造留阶段 6 |

## 共用基础与实际消费

颜色继续使用原 `--ee-*` 的 canvas / surface / ink / line / primary / info / success / warning / danger 映射，不增加独立后台配色。形状保持 4px / 8px 圆角和原有浮层阴影。点阵从 body 移除，现有图形局部规则保留。

| 类别 | 本阶段落地 | 消费位置 |
| --- | --- | --- |
| 字体 | 标题 Space Grotesk，正文 Inter + Noto Sans SC，代码/标注 JetBrains Mono | 原字体配置保持；ThemeToggle 用稳定 SSR SVG |
| 字号 | `--ee-text-meta` 14px、body 16px、reading 17px | 可读标签、日期、提示和后台分组至少 14px；文章列表摘要桌面 18px、手机 16px，标题桌面 28–32px、手机 24px |
| 间距 | 4/8/12/16/24/32px 基础阶梯 | 导航、页尾、列表；不全局覆盖页面工具类 |
| 容器 | page 1440px、reading 720px；后台侧栏 216px | page-shell、文章阅读轴、admin-main；提案 740px 与标题新尺度留阶段 3 一起迁移 |
| 按钮 | 44px 最小高度、双主题语义、可见焦点 | 公共搜索/主题/菜单、既有 button-primary / secondary；保留原禁用与提交行为 |
| 表单 / 反馈 | 输入 16px / 最小 44px；保留 label、错误关联和状态色，长错误可换行 | 登录与后台三类编辑/管理页；不封装业务校验 |
| 列表 / 阅读 | 原 row、分页、阅读容器复用，提取尺度 | admin-list-row、article-reading-main、MarkdownArticle；不造通用表格 API |
| 外壳组件 | SiteHeader、SiteFooter、ThemeToggle、AdminThemeToggle 兼容包装 | 公共/后台/登录共用；页尾 GitHub 仍取真实 profile，原有缓存键保持 |

## 验证入口与结果记录

新增 `tests/e2e/ui-foundation.spec.ts` 覆盖公共 320/390/639/640/768/1024/1279/1280/1440px 双主题，后台 320/390/768/1023/1024/1440px 双主题及 480px 短视口；覆盖主题持久化、背景/色值、横滚、菜单导航焦点、当前路径关闭、写作台认证跳转、后台滚动可达和跨断点清理。原有 E2E 覆盖长文章、代码、表格、发布/搜索、导航焦点循环和助手互斥。

截图与交互分别检查：定向首轮交互 2 项通过，截图发现短屏菜单标题受 flex 压缩，随后固定各区块不收缩并添加标题/首项不重叠断言。截图保存在本地 `.run/ui-foundation/`，不提交重型产物。Vitest 原有固定字面量断言同步为 token + 原 720px 值，保持约束；Lint 已通过。首轮完整 Web quality 通过（149 单元、9 生产质量、8 失败态；Lighthouse 98/100/100/100），E2E 发现页尾品牌链接与页头同名使旧唯一定位失效，已恢复页尾原有纯文字语义；本地原型查询链接触发 Harness 文件名误判，links 检查现剥离 query/fragment 并补测，缺失文件和 durable → active spec 仍拒绝。最终结果以任务 evidence 为准。

最终门禁通过 `python -m tools.harness verify 20260905-ui-foundation` 在隔离 HEAD 执行，含 `npm run quality:web`、`npm run test:e2e`、Harness tests / integrity。运行结果写入自动 evidence，完成后由确定性 close 归档。该任务已关闭，上述命令仅记录当时验收，不作为当前可直接重跑的 active-task 命令。新的回归按当前验证流程选择范围；不能让主工作区的 prepare/typecheck 覆写已有预览的构建目录。

## 恢复与后续成本

产品变更为单独提交，依赖规格先行提交；恢复使用本阶段产品提交的 Git revert 并重新跑受影响检查，无数据迁移。单独回退样式时需要同时回退依赖该 token 的模板/测试。未改动数据库、环境启用开关和用户审查文件。

阶段 2–6 的主要成本分别为真实首页多请求/载荷、阅读页长内容与 SEO、后台保存失败和离页屏障、资源操作恢复、问答竞态及软键盘；共用基础通过不能抵扣这些行为验收，不据此承诺虚构工期。
