---
id: spec-20260822-penpot-about
level: L1
summary: 按 Penpot Gavin_ui_v1 About 板把 /about 改为 statement+coordinates、编号原则与 colophon，资料只绑 GET /profile，并把 /about 补进失败 503 套件
load_when:
  - task:20260822-penpot-about
author: Gavin
task_id: 20260822-penpot-about
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 公开关于页从 sticky 画像栏改为三块布局，且 profile 失败必须整页 503，需要写入 Web 边界。
state_history:
---

# Context

公开 `/about` 当前是 `PublicPageHero` + 左画像 sticky + 原则三卡 + 双 CTA。Penpot `Gavin_ui_v1` revn 342 的 `10 About` 只有 Desktop/Mobile Light：hero（statement|coordinates）+ working principles + colophon。稿上没有头像、SYS.ID、双 CTA；有 dummy `SHANGHAI / UTC+8` 和 `INTER + JETBRAINS MONO`。About 用独立 `useAsyncData('public-profile-about')`。失败套件 `unavailablePages` 目前漏了 `/about`。本页不用 `ProfileCard`。

锁定板：Desktop Light `faa08c08-ba3b-8031-8008-831c0c986858`；Mobile Light `faa08c08-ba3b-8031-8008-831c0cc748d8`。树里 Desktop/Mobile coordinates 均含 EMAIL/GITHUB/RSS。

# Goal

把 `/about` 做成三块中文布局并对齐两块 Light 板；动态字段只来自 `GET /profile`；静态品牌（SYS.ID、公开原则、双 CTA）留下；profile 失败整页错误。

# Non-goals

- 不改 Search、Articles、Books、Projects、Archive、Admin profile 表单、Home `ProfileCard`。
- 不改 profile API，不合并 `public-profile` 与 `public-profile-about` keys。
- 不发明驻地/时区/焦点 Now，不自动把 SYSTEM FACTS 跟仓库同步。
- 不改 `PublicPageHero` 默认。
- 不把 PNG 提交进 Git。

# Acceptance criteria

- AC-1: `/about` 在 1440 与 390、浅色与深色下为 statement+coordinates、编号原则、colophon。桌面 Title→Eyebrow→Intro；390 Title→Intro→Eyebrow→coordinates。中文。主题切换、写作台仍在。头像、`SYS.ID / GVN-01`、公开原则三条、双 CTA 仍在。1024 内容可两栏，Chrome 仍 1280。390/768/1024/1280/1440 不横溢。联系与 CTA ≥44px。
- AC-2: 资料仅 `GET /profile`。有 city/skills/email/github/resume 才显示对应块；无 city 不写 SHANGHAI。RSS 可留 `/rss.xml`。字体说明若保留必须含 Noto Sans SC，禁止 `INTER + JETBRAINS MONO` 漏 Noto，禁止 `LAST REVISED` 自动日期。
- AC-3: profile 失败整页错误。`/about` 加入 failure `unavailablePages`，上游失败 503。缺字段只省略，页面仍 200。
- AC-4: 不改 `ProfileCard` 与 `PublicPageHero` 默认。Home 名片无回归。
- AC-5: 隔离 E2E：字段齐全 / 字段缺失（无 SHANGHAI）/ 静态文案两种夹具都在 / 503。
- AC-6: `apps/web/README.md` 记录关于页三块布局、静态品牌 vs profile 字段、失败 503。

# Risks

- 把 SHANGHAI 写进模板是假 Now。
- 改 `ProfileCard` 打 Home 与后台预览。
- 不补 `/about` 失败测试会让 profile 503 静默变 200。

# Verification plan

- e2e => AC-1, AC-2, AC-4, AC-5
- web-quality => AC-1, AC-3, AC-4, AC-6
