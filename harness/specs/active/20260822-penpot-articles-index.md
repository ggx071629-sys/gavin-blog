---
id: spec-20260822-penpot-articles-index
level: L1
summary: 按 Penpot Gavin_ui_v1 Articles 板把 /articles 改为横向真实栏目筛选与 Date|Title|Meta 行列表，并让 taxonomy 失败与列表失败解耦
load_when:
  - task:20260822-penpot-articles-index
author: Gavin
task_id: 20260822-penpot-articles-index
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 公开文章索引从左侧筛选栏+加框 list card 改为横向栏目条与行列表，且 taxonomy 失败不再整页 503，需要写入 Web 边界。
state_history:
---

# Context

公开 `/articles` 当前是左侧 `filter-rail` + `ArticleCard variant="list"` 加框卡片。`theme-structure` E2E 断言 list 四边框。Penpot 文件 `Gavin_ui_v1`（`file.id` `81f57451-85cc-819d-8008-7c9ef816dd33`，锁定 `revn` 342）的 `04 Articles` 四套板是 intro + 横向筛选 + Date|Title|Meta 行。本 spec **覆盖**加框 list card 视觉合同，不改列表 API。

锁定板：

- Desktop Light `2c68e6bd-bb63-80fc-8008-7cab119ab960`；行 `2c68e6bd-bb63-80fc-8008-7cab43fcf68f`（flex row nowrap）
- Mobile Light `2c68e6bd-bb63-80fc-8008-7cab1876698b`；行 `2c68e6bd-bb63-80fc-8008-7cab4952aae8`（flex column nowrap，Date→Title→Meta）
- Desktop Dark `2c68e6bd-bb63-80fc-8008-7cab1c48d552`
- Mobile Dark `2c68e6bd-bb63-80fc-8008-7cab2326527a`
- 筛选条 Desktop `2c68e6bd-bb63-80fc-8008-7cab43323f43` / Mobile `2c68e6bd-bb63-80fc-8008-7cab487b5955`：flex row nowrap

稿上 ALL/SYSTEMS/DESIGN/TOOLS 是英文 dummy，映射到真实 taxonomy。无 Empty/Error/Loading 板。

# Goal

把 `/articles` 做成横向真实栏目筛选 + Date|Title|Meta 行列表，对齐四套 Articles 板的 1440/390 节奏；文章列表与 taxonomy 分路失败；换筛选时保留旧列表直到最新请求返回。

# Non-goals

- 不改 Search、详情、Books/Projects/Archive/About、Admin、Chrome/Home 重建。
- 不改 OpenAPI、page size 12、`category`/`tag` AND 契约。
- 不删标签条和「搜索全部内容」。
- 不改 `ArticleCard` 默认/featured 变体，不改 `PublicPageHero` 组件默认样式。
- 不发明 Loading/Error/Empty 板或英文 dummy 栏目名。

# Acceptance criteria

- AC-1: `/articles` 在 1440 与 390、浅色与深色下，intro、横向栏目条、列表行对锁定板。桌面行 `Date | Title | Meta` nowrap；390 为 Date→Title→Meta 纵列。栏目为真实名称+计数（含「全部」），无 SYSTEMS/DESIGN/TOOLS。标签与「搜索全部内容」仍在。中文。主题切换、写作台仍可用。390 筛选条 `overflow-x: auto` 锁在条内，页面不横溢。1024 内容可桌面排，Chrome 仍 1280 才切桌面导航。
- AC-2: query 名 `category`/`tag`/`page` 不变。「全部」→ `/articles`（无 category/tag/page）。点栏目或标签重置第 1 页并清掉另一个。翻页保留当时筛选。UI 不提供同时选两个；深链两者按 API AND，高亮两者，翻页保留两者。每页 12。隔离测试用 deterministic seed。
- AC-3: 文章列表失败仍整页错误（`/articles` 上游失败 503）。成功 `[]` 为 200 且仅此时使用「暂时还没有符合条件的已发布文章。」。列表成功 + taxonomy 失败：200 仍渲染列表/空态，筛选区降级并显示「栏目筛选暂不可用」，不画假栏目/假计数，不用空文章句解释 taxonomy 失败。
- AC-4: 无 Loading 板。客户端换 category/tag/page 时保留旧列表，结果区 `aria-busy="true"`，不得把 pending 画成 Empty。只有最新请求世代写 UI；过期 200/4xx/5xx 忽略。SSR 首次等列表结束再出。
- AC-5: Home 默认/featured 卡片结构不变。其它公开索引页 `PublicPageHero` 默认外观不变。`theme-structure` 对 list 的四边框断言改为 Date|Title|Meta 行合同（桌面 row / 390 column）。
- AC-6: 筛选可键盘、焦点可见、触控 ≥44px。
- AC-7: `apps/web/README.md` 记录文章索引为横向真实栏目 + 行列表，以及 taxonomy 失败降级。

# Risks

- 留下 `theme-structure` 四边框 list 断言会把正确的行列表打成失败。
- 继续 `useApiFailure(taxonomyError)` 会让 taxonomy 失败整页 503。
- 筛选 `overflow-x` 加在页面级会造成横溢。
- 改 `ArticleCard` 默认变体或 `PublicPageHero` 默认会打 Home/Books/About。

# Verification plan

- e2e => AC-1, AC-2, AC-4, AC-5, AC-6
- web-quality => AC-1, AC-3, AC-6, AC-7
