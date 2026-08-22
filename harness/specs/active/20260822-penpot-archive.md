---
id: spec-20260822-penpot-archive
level: L1
summary: 按 Penpot Gavin_ui_v1 Archive 板把 /archive 改为两栏 masthead 与年脊 Title|Meta|Date，日期 MM.DD，无栏目显示未分类，阅读时长复用现网公式
load_when:
  - task:20260822-penpot-archive
author: Gavin
task_id: 20260822-penpot-archive
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 公开归档从 Date|Title|Category 短日期行改为年脊 Title|Meta|Date 与 MM.DD，需要写入 Web 边界。
state_history:
---

# Context

公开 `/archive` 当前是 `PublicPageHero` + 当前页按年分组，行 `Date | Title | Category`，日期 `zh-CN` 短格式，组头「N entries」。Penpot `Gavin_ui_v1` revn 342 的 `09 Archive` 只有 Desktop/Mobile Light：masthead + year spine。稿上 `48 NOTES` / `2021 — 2026` 是 dummy。2026 年组行顺序是 Title | Meta | Date；2025/2024 行 children 顺序不同，产品锁 2026。无独立阅读时长字段。page size 20。

锁定板：Desktop Light `faa08c08-ba3b-8031-8008-831bd134df5b`；Mobile Light `faa08c08-ba3b-8031-8008-831bd169cfeb`。2026 行 `831bd31b4dc5`。

# Goal

把 `/archive` 做成中文 masthead + 当前页年脊，桌面 `Title | Meta | Date`，390 先 Date·Meta 再 Title；日期 UTC `MM.DD`；无栏目显示「未分类」；时长与 ArticleCard/详情同一公式。

# Non-goals

- 不改 Search、Articles 列表视觉、Books、Projects、About、文章详情、Admin。
- 不打全量归档 API、不改 page size 20、不改当前页分组。
- 不改 `PublicPageHero` 默认、`ArticleCard` 除数/下限/展示字符串（只抽共享分钟函数）。
- 不发明 `48 NOTES` 或建站年份跨度。
- 不把 PNG 提交进 Git。

# Acceptance criteria

- AC-1: `/archive` 在 1440 与 390、浅色与深色下为两栏/纵列 masthead + 年脊。桌面行 `Title | Meta | Date`（锁 2026 组，不抄 2025/2024 children）。390 先 `MM.DD · 栏目 · N 分钟` 再 Title。年号 `h2`，页面一个 `h1`。组头「N 篇」。中文。主题切换、写作台仍在。1024 内容可桌面年脊，Chrome 仍 1280。390/768/1024/1280/1440 不横溢。触控 ≥44px。
- AC-2: 真实当前页 `GET /articles`。不出现 48 篇、2021—2026、SYSTEMS/MIN dummy。无栏目 Meta 含「未分类」。日期 UTC `MM.DD`。时长 `Math.max(1, Math.ceil(content.length / 500))` 抽到共享函数，ArticleCard 与笔记详情 import 后行为不变。分页仍 20，URL 只改 `page`。年分组仍当前页。
- AC-3: `[]` → 200 现空态。失败整页错误。`/archive?page=999999` → `page=5001`。无 Loading 板：翻页保留旧分组，`aria-busy`，只最新请求写 UI。
- AC-4: 不改 `ArticleCard` 视觉与 `PublicPageHero` 默认。
- AC-5: 隔离 E2E 用独占种子：跨年、无栏目、固定 UTC 日期 `MM.DD`、空、503。
- AC-6: `apps/web/README.md` 记录归档为当前页年脊、`MM.DD`、未分类与共享阅读时长。

# Risks

- 为填 48 篇再打全量列表会打穿有界分页。
- 现 `archive-link` 两套 grid 与稿不对齐，必须覆盖而不是再加断点。
- Archive 内联另一套时长公式会与 ArticleCard 永久分叉。

# Verification plan

- e2e => AC-1, AC-2, AC-3, AC-4, AC-5
- web-quality => AC-1, AC-3, AC-4, AC-6
