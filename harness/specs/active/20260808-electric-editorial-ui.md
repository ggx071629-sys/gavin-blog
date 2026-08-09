---
id: spec-20260808-electric-editorial-ui
level: L1
summary: 以 Stitch Electric Editorial 原型重构主项目公开 UI，并建立可复用的双主题视觉基础
load_when:
  - task:20260808-electric-editorial-ui
author: Gavin
task_id: 20260808-electric-editorial-ui
status: verified
---

# Context

当前公开博客使用分散的 Tailwind slate／blue／purple 样式，缺少语义化设计令牌，且视觉与 `web_prototype/` 中的 Electric Editorial Stitch 原型不一致。本任务是完整 UI 重构的第一阶段，仅交付设计基础、公开壳层与首页纵切面。

Stitch 归档包含独立的浅色与深色设计系统。浅色采用 Chivo、直角结构和高明度编辑网格；深色采用 Hanken Grotesk、蓝黑分层表面及有限软圆角。两套主题不是颜色反转。

# Goal

在不改变 API、数据、公开 URL、认证和业务状态的前提下，建立共享语义令牌和可访问的公开站点壳层，并严格迁移首页、文章卡片及个人名片，使它们可在浅色／深色和桌面／移动四种组合下运行与验收。

# Non-goals

- 不修改 `apps/api/`、数据库模型、迁移或 `packages/contracts/`。
- 不修改后台页面或知识孵化业务 UI。
- 不修改、移动或删除 `my_blog_fork/`。
- 不修改或关闭两个冻结的 GitHub active spec。
- 不恢复、合并或切换 `codex/frozen-github-ingestion-checkpoint`。
- 不提交或推送。

# Acceptance criteria

- 浅色和深色使用同一组语义令牌名称，但分别定义颜色、背景、边框、文字层级、圆角、阴影和交互状态。
- 公开导航、移动菜单、主题切换、跳到正文和页脚保持可用；公开 URL 不变。
- 首页布局、品牌字标、编辑式网格、最近文章区和个人名片与对应 Stitch 原型的结构和视觉层级一致，同时继续使用真实 API 数据。
- `ArticleCard` 与 `ProfileCard` 保留现有可观察业务行为与测试选择器。
- 390px 移动端无横向溢出，触控目标不小于 44px，键盘焦点可见，并尊重减少动态效果偏好。
- 首页在浅色／深色、桌面／移动四种组合下具有可重复的 Playwright 截图证据，并通过适用的 axe WCAG A/AA 检查。
- Web 类型检查、Vitest、生产构建及相关 Playwright 检查通过。

# Risks

- 原型仅提供桌面截图；移动端需要依据原型 HTML 的响应式类与 WCAG AA 约束重排。
- Stitch HTML 依赖 Google Fonts；字体加载失败时必须保留可读的系统字体回退。
- 原型示例内容与真实 API 数据不同，视觉验收应比较结构、排版、层级和状态，而不是硬编码示例文案。
- `web_prototype/dark/screens/search/screenshot.jpg` 损坏，且深色文章截图背景与 HTML/设计系统冲突；后续阶段按有效截图、HTML、设计系统的顺序解释。

# Verification plan

- Vitest：保留并更新导航、主题、个人名片和首页相关组件行为断言。
- Playwright：以固定视口和显式主题覆盖首页四象限截图，并运行 axe WCAG 2.0/2.1 A/AA。
- E2E：运行公开移动导航、主题切换和首页资料交互相关用例。
- Quality：运行 `npm run typecheck`、`npm run test`、`npm run build`，并运行适用的 Playwright 检查。

# Result

第一阶段已完成。公开站点获得独立浅色／深色语义令牌、Electric Editorial 壳层、响应式导航与页脚，以及按主题重排的首页、文章卡片和个人名片。真实 API、URL、SEO、资料交互及后台业务未改变。

应用检查、四象限视觉证据和 Lighthouse 结果见 [application evidence](../../verification/evidence/20260808-electric-editorial-ui.application.json)；Harness 确定性检查见 [harness evidence](../../verification/evidence/20260808-electric-editorial-ui.json)。
