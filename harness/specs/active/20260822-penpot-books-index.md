---
id: spec-20260822-penpot-books-index
level: L1
summary: 按 Penpot Gavin_ui_v1 Books 板把 /books 改为全宽 hero、当前页在读高亮与 Date|书名|状态 ledger，不发明进度或全库计数
load_when:
  - task:20260822-penpot-books-index
author: Gavin
task_id: 20260822-penpot-books-index
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 公开读书索引从封面网格改为在读高亮加 ledger 行，失败/空态与分页语义需要写入 Web 边界。
state_history:
---

# Context

公开 `/books` 当前是 `PublicPageHero` + 2/3 列封面卡 `BookCard`。Penpot 文件 `Gavin_ui_v1`（`file.id` `81f57451-85cc-819d-8008-7c9ef816dd33`，锁定 `revn` 342）的 `07 Books` 只有 Desktop/Mobile Light：hero + current reading + shelf ledger。无 Dark/Empty/Error/Loading 板。稿上 PAGE 进度、笔记条数、`CURRENTLY READING`、`12 BOOKS · UPDATED AUG 2026` 是 dummy。`BookCard` 仅本页使用。

锁定板：Desktop Light `faa08c08-ba3b-8031-8008-831aa55747f5`；Mobile Light `faa08c08-ba3b-8031-8008-831aa6062272`。桌面 ledger 行 `831acdce96ee` 为 Date | Title+Author | Status；390 行 `831ad3d05f1d` 为 Date→Title→Author→Status。

# Goal

把 `/books` 做成全宽中文 hero、可选当前页「在读」高亮与 shelf ledger，对齐两块 Light 板的 1440/390 节奏；数据仍走 `GET /books` 与 page size 12。

# Non-goals

- 不改 Search、Articles、Projects、Archive、About、书摘详情、Admin、Chrome/Home。
- 不改 OpenAPI、page size、阅读状态枚举。
- 不改 `PublicPageHero` 默认、`ArticleCard`、`ProjectCard`、`ProfileCard`。
- 不发明全库计数、页码进度、深色板、Loading 骨架。
- 不把 PNG 提交进 Git。

# Acceptance criteria

- AC-1: `/books` 在 1440 与 390、浅色与深色下为 hero + 可选在读块 + ledger 行，不再是封面网格。桌面 ledger `Date | 书名+作者 | 状态`；390 为 Date→Title→Author→Status。日期 `YYYY.MM`。中文。主题切换、写作台仍在。1024 内容可桌面排，Chrome 仍 1280 才切桌面导航。390/768/1024/1280/1440 页面不横溢。触控 ≥44px。
- AC-2: 真实 `GET /books`。不出现 `PAGE 416/616`、`APPLIED · 14 NOTES`、`12 BOOKS`、稿书名。在读块只在当前页存在 `reading_status=reading` 时渲染，文案为「在读」不是「当前阅读」/currently reading；只用标题、作者、可选 summary、CTA→`public_path`。Ledger 含当前页全部条目。分页仍 12，URL 只改 `page`。
- AC-3: `[]` → 200 现空态。列表失败整页错误。无 Loading 板：翻页保留旧列表，结果区 `aria-busy`，只最新请求写 UI。
- AC-4: 不改共享组件默认。Home 名片与 Articles hero 无回归。
- AC-5: 隔离 E2E 用独占种子：有在读 / 无在读 / 翻页显隐 / 空 / `/books` 503。
- AC-6: `apps/web/README.md` 记录读书索引为在读高亮 + ledger 行，以及当前页 reading 语义。

# Risks

- 把第 1 条当成在读会在只有 completed 时造假。
- 改 `PublicPageHero` 默认会打 Articles/About。
- 漏网 `BookCard` 引用会破封面卡详情以外的面（当前仅本页）。

# Verification plan

- e2e => AC-1, AC-2, AC-3, AC-4, AC-5
- web-quality => AC-1, AC-3, AC-4, AC-6
