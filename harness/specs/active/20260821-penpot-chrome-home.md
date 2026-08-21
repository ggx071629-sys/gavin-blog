---
id: spec-20260821-penpot-chrome-home
level: L1
summary: 按 Penpot Gavin_ui_v1 Chrome 与 Home 对齐公开站壳层和首页视觉，并切换中文标题字体为自托管 Noto Sans SC
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
documentation_reason: 公开站壳层、移动菜单合同和标题字体从 Hanken Grotesk 改为 Noto Sans SC 与 Inter 分流，需要同步 Web 边界与产品基线。
state_history:
---

# Context

公开站已是 Electric Editorial 双主题，`--ee-*` 浅色值与 Penpot `modes/light` 一致，深色值与 `previews/dark` 一致。Penpot 文件 `Gavin_ui_v1`（`file.id` `81f57451-85cc-819d-8008-7c9ef816dd33`，锁定 `revn` 342）里，`02 Chrome` 与 `03 Home` 是本刀范围。Home 有桌面/移动 × 浅/深四套板。产品面（主题切换、写作台、`ProfileCard`、中文文案）必须留下。文章详情 V2 已关闭，不重做。

权威：视觉节奏听锁定板；行为、路由、API、失败语义听仓库。深色 token 只读 `previews/dark`，禁止用未激活的 `modes/dark` resolved 值。开实现前复核 `revn`；若上升，先 diff 锁定板。

# Goal

把公开站顶栏、页脚、移动菜单和首页 Hero/最近文章区对齐 Penpot Chrome + Home 的 1440/390 节奏，中文用自托管 Noto Sans SC 400/700、拉丁用 Inter、代码仍 JetBrains Mono，同时保留现有产品面和公开契约。

# Non-goals

- 不改 API、OpenAPI、数据库、认证、URL、搜索契约或孵化后台。
- 不重做 `/notes/{year}/{month}/{slug}`，不做 Articles/Books/Projects/Archive/About/Search/Admin/System 页。
- 不实现 Home 的 Now 区块，不编造文章或指标。
- 不把导航或 Hero 改成 Penpot 英文 dummy。
- 不删除主题切换、写作台、`ProfileCard`、跳到正文。
- 不把主导航断点从 `xl`/1280 改到 1024。
- 不托管 Noto/Inter 800，不请求 Google Fonts，不把 PNG 参考图提交进 Git。
- 不新增 `--penpot-*` 平行 token，不把 Hanken 留在标题栈。

# Acceptance criteria

- AC-1: `/` 在宽 1440 与 390、浅色与深色下，顶栏、页脚、Hero、最近文章区的层级和间距与锁定板一致：Desktop Light `2c68e6bd-bb63-80fc-8008-7ca93c640cc8`、Mobile Light `2c68e6bd-bb63-80fc-8008-7ca93fd54f51`、Desktop Dark `2c68e6bd-bb63-80fc-8008-7ca941f21521`、Mobile Dark `2c68e6bd-bb63-80fc-8008-7ca945979f58`。主题切换、写作台、跳到正文仍可用。对照忽略已知产品面差异（中文文案、名片、双 CTA、无 Now）。
- AC-2: 首页仍经真实公开 API 读取文章列表和 profile。有文章则渲染真实卡片（可多于稿上 3 条）；有 profile 则渲染 `ProfileCard`。隔离测试使用 deterministic seed，不依赖开发库。不出现 Now 区块或虚构指标。空列表仍是现有空态文案。
- AC-3: 中文正文/标题计算字体含 Noto Sans SC；仅托管 400 与 700，稿上 800 映射为 `font-weight: 700`。拉丁含 Inter（标题 700）。等宽仍是 JetBrains Mono。无 Hanken 引用，无 Google Fonts 请求。woff2 失败不横向溢出。Evidence 记录字体体积、请求数、首页 LCP/CLS。桌面 Lighthouse Performance、Accessibility、Best Practices、SEO 均 ≥90。
- AC-4: 公开 URL、失败分类、44×44 CSS px 触控、可见焦点、`prefers-reduced-motion` 关闭非必要运动均不回退。文章阅读页顶栏压缩行为仍在。
- AC-5: 390 与 1440 无横向溢出。768、1024、1280 无溢出或裁切；1024 仍为移动导航，1280 起为桌面导航。Penpot 1024 Desktop header 只记录为差异，不当失败。
- AC-6: 390 下移动菜单为 overlay dialog：`role="dialog"`、`aria-modal="true"`、可见标题、`aria-expanded`/`aria-controls`、打开后焦点进入并 Tab 循环、背景 inert、滚动锁定、Escape/遮罩/导航/路由关闭并把焦点送回按钮。视口到 `xl` 必须关闭并清 inert 与滚动锁。
- AC-7: `apps/web/README.md` 记录壳层、overlay 合同与 Noto/Inter 字体；`harness/docs/product/brief.md` 将标题字体从 Hanken Grotesk 改为 Noto Sans SC + Inter 分流。

# Risks

- CJK 子集体积可能把 Lighthouse Performance 打到 90 以下；只允许缩 subset 或减少字重，禁止全量 Noto，禁止下调门槛。
- Overlay 若没有 inert、滚动锁和断点清理，会与桌面导航叠层或把焦点困在不可见面板。
- 把稿上英文 Display 或 Now 区块当数据会破坏站点语言和 API 边界。
- 压缩顶栏若做成全局行为会改变非文章页；压缩仍只绑定文章路由。
- `package-lock.json` 变更会抬升到 release 门禁；不得用该包门禁独占多条 AC。

# Verification plan

- e2e => AC-1, AC-2, AC-4, AC-5, AC-6
- web-quality => AC-3, AC-4, AC-7
- harness-integrity => AC-7
- release => AC-3
