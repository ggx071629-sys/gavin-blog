---
id: spec-20260822-penpot-search
level: L1
summary: 按 Penpot Gavin_ui_v1 Search 板把公开 /search 改为全页内容区，并锁死 Idle/Loading/Results/Empty 与最新请求竞态
load_when:
  - task:20260822-penpot-search
author: Gavin
task_id: 20260822-penpot-search
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 公开搜索桌面布局从已关闭的居中卡片合同改为全页内容区，且状态机与 503 失败语义需要写进 Web 边界。
state_history:
---

# Context

公开 `/search` 当前在 `min-width: 1024px` 使用已关闭 spec `20260809-sync-light-search-layout` 的居中卡片（`max-w-4xl` / 896px、边框与阴影）。Penpot 文件 `Gavin_ui_v1`（`file.id` `81f57451-85cc-819d-8008-7c9ef816dd33`，锁定 `revn` 342）的 `11 Search` 是全页站点壳层 + 内容区。本 spec **明文覆盖**该居中卡片视觉合同，不改搜索 API。

权威：Results / Empty / Loading 节奏听锁定板；`q` 校验、分页、FTS、失败分类听仓库。Search **没有深色板**，深色只回归 `--ee-*` 几何。Error 板不在本段视觉验收：`/search?q=failure` 仍是整页 503 + `error.vue`。

锁定板（视觉要验收 Light / Empty / Loading；Error 只记录）：

- Desktop Light `faa08c08-ba3b-8031-8008-831c3d4064e1`
- Mobile Light `faa08c08-ba3b-8031-8008-831c3d742685`
- Desktop Empty `153af549-5bcc-80a6-8008-835e5bbd78e6`
- Mobile Empty `153af549-5bcc-80a6-8008-835ec08a8e6b`
- Desktop Loading `153af549-5bcc-80a6-8008-835e7ed88f99`
- Mobile Loading `153af549-5bcc-80a6-8008-835eddfe149f`
- Desktop Error `153af549-5bcc-80a6-8008-835e9081d3bf`（不验收外观）
- Mobile Error `153af549-5bcc-80a6-8008-835eeee1cbf1`（不验收外观）

# Goal

把 `/search` 做成全页内容区，对齐 Search Light / Empty / Loading 板的 1440/390 节奏，并用 `q` 与最新请求世代驱动 Idle / Loading / Results / Empty；上游失败保持现有 503 分类。

# Non-goals

- 不改 OpenAPI、FTS、`q` 1–120 校验、page size、limit/offset。
- 不为装饰 chips 发明 type-filter API。
- 不把 Error 板画进 200，不改 `error.vue` 外观。
- 不重做 Home/Chrome、Articles、Books、Projects、Archive、About、Admin、System。
- 不把主导航断点从 1280 改到 1024。
- 不把 PNG 参考图提交进 Git，不做像素 diff CI。

# Acceptance criteria

- AC-1: `/search` 在宽 1440 与 390、浅色与深色下，内容区是全页舞台而不是 ≥1024 的 896px 居中卡。Results 节奏对 Desktop/Mobile Light 板；Empty 对 Empty 板；客户端 Loading 对 Loading 板。主题切换、写作台仍可用。中文文案。「关闭」回到 `/`。对照忽略稿上英文 dummy。
- AC-2: 同一时刻只处于 Idle（无 `q`，不请求搜索 API，清掉上一轮命中）、Loading（客户端 `pending && q`，**不保留**旧命中）、Results（最新 200 且有条目）、Empty（最新 200 且 `[]`）。SSR 带 `q` 时等该请求结束再出 Results/Empty/Error，不先画假 Loading。只有最新请求世代可以写 UI；更早的慢 200 或错误不得覆盖。
- AC-3: `/search?q=failure` 仍为 **503** 且渲染现有 `error.vue`，不是 200 空搜，也不是页内 Error 板。Empty 文案与 Idle 文案不同。
- AC-4: chips 不可点（不是链接或按钮）。分页保留 `q`；当前页有 `aria-current="page"` 或等价。提交按钮与 Enter 都能提交。
- AC-5: 390、768、1024、1280、1440 无页面横向溢出。1024 已是桌面搜索内容布局，Chrome 仍为移动导航；1280 起桌面导航。
- AC-6: `form role="search"`；输入有可访问名称（不得只靠 placeholder）；Loading 结果区 `aria-busy="true"` 且状态可被感知；触控目标 ≥44px；可见焦点。
- AC-7: 隔离 E2E 使用 deterministic seed（不依赖开发库）：冻结命中标题可经真实 `GET /search` 找到；冻结未命中词为 200 Empty；第 2 页保留 `q`；先慢后快只显示快请求结果。`search-theme` 断言全页几何，不再断言 896px 卡片。
- AC-8: `apps/web/README.md` 记录公开搜索为全页内容区、Idle≠Empty、Loading 不保留旧命中、失败仍 503。

# Risks

- 留下 `search-theme` 的 896px 卡片断言会把正确的全页实现打成失败。
- Loading 若继续渲染上一查询命中，会把旧结果读成当前结果。
- 把 Error 板做成 200 会打穿失败分类合同。
- 1024 内容已桌面、壳仍汉堡是相对 Penpot 1024 header 的故意差异，不当缺陷。

# Verification plan

- e2e => AC-1, AC-2, AC-4, AC-5, AC-6, AC-7
- web-quality => AC-1, AC-3, AC-6, AC-8
