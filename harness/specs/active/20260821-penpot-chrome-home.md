---
id: spec-20260821-penpot-chrome-home
level: L1
summary: 按 Penpot Gavin_ui_v1 Chrome、Home 与 Mobile Menu 对齐公开站壳层和首页，并固化 <=639 全屏、640–1279 抽屉的响应式导航
load_when:
  - task:20260821-penpot-chrome-home
author: Gavin
task_id: 20260821-penpot-chrome-home
status: active
verification_profile: focused
verification_escalation: Root package-lock.json will change for @fontsource/noto-sans-sc; release is risk-derived and does not solely cover any AC.
documentation_impact: required
documentation_targets:
  - apps/web/README.md
  - harness/docs/product/brief.md
documentation_reason: 公开站壳层、手机全屏菜单、平板抽屉合同和标题字体分流发生用户可见变化，需要同步 Web 边界与产品基线。
state_history:
---

# Context

公开站已是 Electric Editorial 双主题，`--ee-*` 浅色值与 Penpot `modes/light` 一致，深色值与 `previews/dark` 一致。Penpot 文件 `Gavin_ui_v1`（`file.id` `81f57451-85cc-819d-8008-7c9ef816dd33`，锁定 `revn` 342）里，`02 Chrome` 与 `03 Home` 是本刀范围。Home 有桌面/移动 × 浅/深四套板。产品面（主题切换、写作台、`ProfileCard`、中文文案）必须留下。文章详情 V2 已关闭，不重做。

已核验的手机菜单目标板为 Mobile Menu / Overlay `153af549-5bcc-80a6-8008-8364c3a8c208`。该板约束 `<=639px` 的打开态；Penpot 未给出完成态的平板菜单，因此 `640–1279px` 保留仓库现有右侧抽屉，不把手机全屏布局外推到平板。

权威：视觉节奏听锁定板；行为、路由、API、失败语义听仓库。深色 token 只读 `previews/dark`，禁止用未激活的 `modes/dark` resolved 值。开实现前复核 `revn`；若上升，先 diff 锁定板。

# Goal

把公开站顶栏、页脚、手机菜单和首页 Hero/最近文章区对齐 Penpot Chrome + Home；`<=639px` 使用 Mobile Menu 全屏覆盖，`640–1279px` 保留现有抽屉，`>=1280px` 保持桌面导航，同时保留现有产品面、公开契约和字体分流。

# Non-goals

- 不改 API、OpenAPI、数据库、认证、URL、搜索契约或孵化后台。
- 不重做 `/notes/{year}/{month}/{slug}`，不做 Articles/Books/Projects/Archive/About/Search/Admin/System 页。
- 不实现 Home 的 Now 区块，不编造文章或指标。
- 不把导航或 Hero 改成 Penpot 英文 dummy。
- 不删除主题切换、写作台、`ProfileCard`、跳到正文。
- 不把主导航断点从 `xl`/1280 改到 1024。
- 不托管 Noto/Inter 800，不请求 Google Fonts，不把 PNG 参考图提交进 Git。
- 不新增 `--penpot-*` 平行 token，不把 Hanken 留在标题栈。
- 不把 `<=639px` 的全屏菜单样式推断或扩展到 `640–1279px`。
- 不从手机菜单删除搜索或写作台；不把写作台提升为主导航同级。

# Acceptance criteria

- AC-1: `/` 在宽 1440 与 390、浅色与深色下，顶栏、页脚、Hero、最近文章区的层级和间距与锁定板一致：Desktop Light `2c68e6bd-bb63-80fc-8008-7ca93c640cc8`、Mobile Light `2c68e6bd-bb63-80fc-8008-7ca93fd54f51`、Desktop Dark `2c68e6bd-bb63-80fc-8008-7ca941f21521`、Mobile Dark `2c68e6bd-bb63-80fc-8008-7ca945979f58`。主题切换、写作台、跳到正文仍可用。对照忽略已知产品面差异（中文文案、名片、双 CTA、无 Now）。
- AC-2: 首页仍经真实公开 API 读取文章列表和 profile。有文章则渲染真实卡片（可多于稿上 3 条）；有 profile 则渲染 `ProfileCard`。隔离测试使用 deterministic seed，不依赖开发库。不出现 Now 区块或虚构指标。空列表仍是现有空态文案。
- AC-3: 中文正文/标题计算字体含 Noto Sans SC；仅托管 400 与 700，稿上 800 映射为 `font-weight: 700`。拉丁含 Inter（标题 700）。等宽仍是 JetBrains Mono。无 Hanken 引用，无 Google Fonts 请求。woff2 失败不横向溢出。Evidence 记录字体体积、请求数、首页 LCP/CLS。桌面 Lighthouse Performance、Accessibility、Best Practices、SEO 均 ≥90。
- AC-4: 公开 URL、失败分类、44×44 CSS px 触控、可见焦点、`prefers-reduced-motion` 关闭非必要运动均不回退。文章阅读页顶栏压缩行为仍在。
- AC-5: 320、390、414、640、768、1024、1279、1280 与 1440 均无横向溢出或裁切；`<=639px` 为手机全屏菜单，`640–1279px` 为现有右侧抽屉，1280 起为桌面导航。Penpot 的 1024 Desktop header 只记录为已知差异，不当失败。
- AC-6: 所有小于 1280px 的菜单继续使用 `role="dialog"`、`aria-modal="true"`、可见标题和正确的 `aria-expanded`/`aria-controls`；打开后焦点进入并循环，背景 inert、body 锁滚；Escape、遮罩、菜单导航和路由变化关闭，显式关闭把焦点送回触发按钮；进入 1280px 时关闭并清理 inert 与滚动锁。
- AC-7: `apps/web/README.md` 记录壳层、overlay 合同与 Noto/Inter 字体；`harness/docs/product/brief.md` 将标题字体从 Hanken Grotesk 改为 Noto Sans SC + Inter 分流。
- AC-8: `<=639px` 打开态覆盖整个可视视口并对齐 Mobile Menu / Overlay `153af549-5bcc-80a6-8008-8364c3a8c208`，使用层级清晰的大尺寸导航卡片；菜单内可访问顺序严格为文章、读书、项目、归档、关于、搜索，写作台位于主导航之后并作为低优先级独立入口。每个触控目标至少 44×44 CSS px，相邻目标间距至少 8px。`640–1279px` 仍使用现有抽屉形态和现有平板层级，不伪造 Penpot 未定义的布局。

# Risks

- CJK 子集体积可能把 Lighthouse Performance 打到 90 以下；只允许缩 subset 或减少字重，禁止全量 Noto，禁止下调门槛。
- Overlay 若没有 inert、滚动锁和断点清理，会与桌面导航叠层或把焦点困在不可见面板。
- 把稿上英文 Display 或 Now 区块当数据会破坏站点语言和 API 边界。
- 压缩顶栏若做成全局行为会改变非文章页；压缩仍只绑定文章路由。
- `package-lock.json` 变更会抬升到 release 门禁；不得用该包门禁独占多条 AC。
- 手机与平板共用同一 dialog 生命周期但视觉结构不同；跨 639px 调整只应换布局，不能制造重复焦点项或失效的 focus trap。
- 为手机加入菜单内搜索时，必须避免隐藏副本进入 Tab 顺序；平板现有顶部搜索入口不得被无意移除。

# Verification plan

- e2e => AC-1, AC-2, AC-4, AC-5, AC-6, AC-8
- web-quality => AC-3, AC-4, AC-5, AC-6, AC-7, AC-8
- harness-integrity => AC-7
- release => AC-3
