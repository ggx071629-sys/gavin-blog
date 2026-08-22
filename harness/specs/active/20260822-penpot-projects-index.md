---
id: spec-20260822-penpot-projects-index
level: L1
summary: 按 Penpot Gavin_ui_v1 Projects 板把 /projects 改为全宽 hero、本页第一条 lead 与 ledger 行，去掉 sticky 网格和假状态分数
load_when:
  - task:20260822-penpot-projects-index
author: Gavin
task_id: 20260822-penpot-projects-index
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 公开项目索引从 sticky 双栏卡片网格改为 lead + ledger，失败/空态与 featured 语义需要写入 Web 边界。
state_history:
---

# Context

公开 `/projects` 当前是左侧 sticky `PublicPageHero` + 两列卡，第 1 张 `featured`。Penpot `Gavin_ui_v1` revn 342 的 `08 Projects` 只有 Desktop/Mobile Light：全宽 hero + active project + project ledger。稿上 `ACTIVE · RELEASE CANDIDATE`、技术栈、`435 / 435`、`MAINTAINED` 是 dummy。`PublicProject` 没有状态/分数/技术栈字段。`ProjectCard` 仅本页使用。

锁定板：Desktop Light `faa08c08-ba3b-8031-8008-831b9fe67f81`；Mobile Light `faa08c08-ba3b-8031-8008-831ba0164abc`。

# Goal

把 `/projects` 做成全宽中文 hero、当前页第一条的视觉 lead 与其余条目 ledger，对齐两块 Light 板；数据仍走 `GET /projects` 与 page size 12。

# Non-goals

- 不改 Search、Articles、Books、Archive、About、项目详情、Admin、Chrome/Home。
- 不改 OpenAPI、不发明项目状态机/质量分数/技术栈字段。
- 不改 `PublicPageHero` 默认、`BookCard`、`ArticleCard`、`ProfileCard`。
- 不把第 1 条包装成 featured/active/主项目。
- 不把 PNG 提交进 Git。

# Acceptance criteria

- AC-1: `/projects` 在 1440 与 390、浅色与深色下为全宽 hero + lead + ledger，不再是 sticky 双栏卡片网格。桌面 ledger `序号 | 名称+摘要 | 次级元信息`；390 列改行。中文。主题切换、写作台仍在。1024 内容可桌面排，Chrome 仍 1280。390/768/1024/1280/1440 不横溢。触控 ≥44px。
- AC-2: 真实 `GET /projects`。不出现假状态、假分数、假技术栈、`ACTIVE`/`featured`/`主项目` 文案。Lead = 当前页 `items[0]`；ledger 不重复该条。序号按整页位置（lead 01 不画在 ledger，第一条 ledger 为 02）。0 条：现空态不渲染 lead。1 条：只 lead。`page=2` 的 lead 等于该页第一条。分页仍 12，URL 只改 `page`。次级元信息只用「N 篇笔记」或省略。
- AC-3: `[]` → 200 现空态。失败整页错误。`/projects?page=2` 空 200 与 `page=3` 503 挂钩仍在。无 Loading 板：翻页保留旧列表，`aria-busy`，只最新请求写 UI。
- AC-4: 不改共享组件默认。Home/Books/Articles 无回归。
- AC-5: 隔离 E2E 用独占种子：0 / 1 / 多条 / `page=2` lead / 503。
- AC-6: `apps/web/README.md` 记录项目索引为 lead + ledger，以及 lead 无 featured 语义。

# Risks

- 改 `PublicPageHero.vue` 默认会打其它索引。
- 失败套件依赖 `/projects?page=2` 空文案挂钩。
- 把 lead 写成 featured 会发明 Now。

# Verification plan

- e2e => AC-1, AC-2, AC-3, AC-4, AC-5
- web-quality => AC-1, AC-3, AC-4, AC-6
