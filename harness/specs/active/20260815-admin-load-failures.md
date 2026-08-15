---
id: spec-20260815-admin-load-failures
level: L1
summary: 让孵化与后台编辑加载失败走共享失败分类，不再伪装成空成功
load_when:
  - task:20260815-admin-load-failures
author: Gavin
task_id: 20260815-admin-load-failures
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 后台失败分类从列表页扩展到孵化与编辑加载，需要同步 Web 边界说明。
state_history:
---

# Context

2026-08-15 审计 AUD26-003：公开页与后台列表已区分空数据与上游故障，但孵化概览、工作台壳和内容编辑页在 API 失败时显示「没有待办」或空白编辑器。`failure-state-contract` 未覆盖这些面。

# Goal

孵化概览、工作台壳、后台内容编辑/预览/新建依赖加载，以及孵化三池列表在上游失败时使用与公开页相同的失败分类，不再伪装成空成功。

# Non-goals

- 不改公开 SSR 失败语义。
- 不改 OpenAPI、数据库或认证/CSRF。
- 不把可选健康检查（检索/LLM health）提升为整页失败。
- 不改两条 GitHub frozen spec。

# Acceptance criteria

- AC-1: `/admin/incubator` 在 overview 上游 5xx 或网络失败时不渲染「当前没有需要处理的异常或待办」；SSR 保留对应 5xx/503。
- AC-2: `IncubatorShell` 不再把 overview 失败吞成 `null` 并显示 0 角标。
- AC-3: 文章/项目/书摘编辑与文章预览、名片页在主资源加载失败时走 `useApiFailure`，不渲染空白编辑器。
- AC-4: 新建文章的栏目/标签、新建项目的文章选项，以及孵化三池/任务列表加载失败时不显示「尚无/没有内容」空成功。
- AC-5: `apps/web/README.md` 记录上述后台加载失败语义；契约测试覆盖这些页面或共享 composable。

# Risks

后台加载失败会从空白页变为错误页，这是有意收紧。可选 health 失败不得拖垮详情页。

# Verification plan

- web-quality => AC-1, AC-2, AC-3, AC-4, AC-5
- api-lint => AC-5
- api-tests => AC-5
