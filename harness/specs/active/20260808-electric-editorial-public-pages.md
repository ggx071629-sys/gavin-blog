---
id: spec-20260808-electric-editorial-public-pages
level: L1
summary: 按 Stitch Electric Editorial 原型完成全部公开内容页面的双主题 UI 重构
load_when:
  - task:20260808-electric-editorial-public-pages
author: Gavin
task_id: 20260808-electric-editorial-public-pages
status: verified
---

# Context

第一阶段已经建立 Electric Editorial 双主题令牌、公开站点壳层、首页、文章卡片和个人名片。其余公开路由仍使用旧的 slate／blue／rounded 视觉，无法与 `web_prototype/` 中的浅色和深色 Stitch 原型形成一致体验。

原型与现有路由／文件映射如下：

| 原型 | 路由 | 页面文件 | 状态 |
| --- | --- | --- | --- |
| light/dark `articles` | `/articles` | `apps/web/pages/articles/index.vue` | 两套原型；深色截图外层白底与 HTML／设计系统冲突，以 HTML 和深色令牌纠正 |
| dark `article-nuxt3-performance` | `/notes/:year/:month/:slug` | `apps/web/pages/notes/[year]/[month]/[slug].vue` | 仅深色原型；浅色由 light 设计系统和同族详情页派生 |
| light/dark `reading` | `/books` | `apps/web/pages/books/index.vue` | 两套原型 |
| 无直接原型 | `/books/:year/:month/:slug` | `apps/web/pages/books/[year]/[month]/[slug].vue` | 由 reading 卡片与文章详情的同主题规则派生 |
| dark `projects` | `/projects` | `apps/web/pages/projects/index.vue` | 仅深色原型；浅色由 light project-detail 与设计系统派生 |
| light `project-detail` / dark `project-ai-workflow` | `/projects/:slug` | `apps/web/pages/projects/[slug].vue` | 两套详情原型，真实模型不含独立 hero／角色／时间线字段 |
| light/dark `archive` | `/archive` | `apps/web/pages/archive.vue` | 两套原型 |
| light/dark `about` | `/about` | `apps/web/pages/about.vue` | 两套原型；原型人物图片和联系信息不是当前公开 API 数据，不能硬编码冒充真实资料 |
| light/dark `search` | `/search` | `apps/web/pages/search.vue` | 深色截图损坏为纯黑，但 HTML 有效；按 HTML 实现深色搜索界面 |
| dark `404` | Nuxt 错误页 | `apps/web/error.vue`（待创建） | 仅深色原型；浅色由同一结构与 light 设计系统派生 |

解释优先级固定为：有效截图 → 对应 HTML → 对应主题设计系统 → 最近的页面族原型。原型中的示例内容仅用于排版，不替换真实 API 数据。

# Goal

在不改变 API、数据模型、公开 URL、认证、SEO 契约和业务状态机的前提下，完成全部公开内容列表、详情、归档、关于、搜索与错误页的 Electric Editorial 重构，并在浅色／深色、桌面／移动四象限下可重复验证。

# Non-goals

- 不修改 `apps/api/`、数据库、迁移、`packages/contracts/` 或公开 URL。
- 不为原型 Hero 图新增 API 字段；Markdown 首图存在时由正文自然展示，否则使用排版型首屏。
- 不把原型示例人物、履历、技术栈、项目指标或书籍硬编码为真实内容。
- 不修改任何管理后台或知识孵化页面。
- 不修改、移动或删除 `my_blog_fork/`。
- 不修改、解冻或关闭 `20260807-github-discovery-ingestion` 与 `20260807-github-source-crawler`。
- 不恢复或合并 `codex/frozen-github-ingestion-checkpoint`。
- 不提交或推送。

# Acceptance criteria

- 十个公开页面文件和 Nuxt 错误页统一使用第一阶段语义令牌及公共阅读组件，不再依赖页面级 slate／rounded 旧主题表达。
- 文章列表保留栏目、标签、计数、查询参数和分页；桌面采用侧栏索引，移动端安全折叠为可横向换行的筛选区。
- 文章、项目和读书详情保留真实内容、Markdown、外链、参考资料、关联文章、SEO 和 404 行为。
- 项目与读书列表按对应 Stitch 页面建立高密度编辑卡片；缺少封面或 Hero 时提供不伪造内容的排版型占位。
- 归档保留按年分组和分页；搜索保留查询、禁用状态、结果类型、分页、`noindex` 及 hydration 行为。
- 404 提供返回首页、搜索和浏览文章入口，并对浅色／深色分别呈现，而不是简单颜色反转。
- 所有小号文字对所在背景满足 WCAG AA；酸性绿在浅色主题中只承担信号／填充／边框，除非实际对比度达到要求。
- 390px 宽度无横向溢出，交互目标至少 44px，焦点可见，减少动态效果偏好有效。
- 文章列表、文章详情、项目列表／详情、读书列表／详情、归档、关于、搜索和 404 的代表页覆盖四象限视觉检查；适用页面通过 axe A/AA。
- Web 类型检查、Vitest、生产构建、相关 Playwright E2E 和质量门禁通过。

# Risks

- 当前 API 没有项目 Hero、项目角色／时间线／技术栈及文章 Hero 字段；硬编码原型示例会产生事实错误，因此以真实 Markdown 和排版结构替代。
- 读书详情没有直接原型；需使用阅读卡片的书籍元数据模式和文章详情的长文模式组合，属于有依据的派生而非逐像素复刻。
- 深色 articles、about 截图存在白色外层画布异常，search 截图完全损坏；若机械复刻会破坏主题一致性和可访问性，必须按有效 HTML／设计系统纠正。
- 全页面视觉矩阵成本较高；自动截图按页面族取代表页，同时对所有公共索引页面执行无溢出和 axe 扫描。

# Verification plan

- Vitest：覆盖新增公共组件的状态、链接、封面回退和语义输出；保留现有工具与组件测试。
- E2E：覆盖移动导航、主题、公开详情、搜索、分页和 SEO 发现闭环。
- Visual：固定数据下按 light/dark × 1440/390 生成页面族代表截图，并人工对照 Stitch。
- Accessibility：Playwright + axe 对公开索引、固定数据详情和 404 执行 WCAG 2.0/2.1 A/AA；检查水平溢出和焦点状态。
- Quality：运行 Nuxt typecheck、Vitest、生产构建、适用 Playwright 与 Lighthouse。
- Harness：生成索引并运行 `python -m tools.harness verify 20260808-electric-editorial-public-pages`，提交紧凑 evidence manifest，不提交截图或重型报告。

# Result

第二阶段已完成。文章、项目、阅读、归档、关于、搜索、三类详情页和 Nuxt 错误页均迁移到 Electric Editorial 双主题公共组件与语义令牌。项目和文章没有伪造原型中的 Hero／技术栈字段；读书与项目缺图时使用排版型回退；关于页只展示公开资料 API 实际返回的数据。

实现中主动纠正了三项问题：浅色酸性绿小字改用满足 AA 的深电蓝；书籍评分改为屏幕阅读器文本与视觉星级分离；正文首个 Markdown H1 在公开详情中隐藏，避免和页面主标题重复。深色损坏或冲突截图按对应 HTML 与设计系统还原，没有机械复制白底或纯黑错误状态。

应用检查、40 张本地四象限截图、人工视觉抽样、axe 和 Lighthouse 结果见 [application evidence](../../verification/evidence/20260808-electric-editorial-public-pages.application.json)；Harness 确定性检查见 [harness evidence](../../verification/evidence/20260808-electric-editorial-public-pages.json)。
