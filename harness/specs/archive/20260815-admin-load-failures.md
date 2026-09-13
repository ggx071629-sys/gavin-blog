---
id: archive-20260815-admin-load-failures
level: L2
summary: 让孵化与后台编辑加载失败走共享失败分类，不再伪装成空成功
load_when:
  - task:20260815-admin-load-failures
author: Gavin
task_id: 20260815-admin-load-failures
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/README.md
documentation_reason: 后台失败分类从列表页扩展到孵化与编辑加载，需要同步 Web 边界说明。
state_history:
---

# 20260815-admin-load-failures

Deterministic compressed record. The original active spec remains in Git history.

## Goal

孵化概览、工作台壳、后台内容编辑/预览/新建依赖加载，以及孵化三池列表在上游失败时使用与公开页相同的失败分类，不再伪装成空成功。

## Acceptance criteria

- AC-1: `/admin/incubator` 在 overview 上游 5xx 或网络失败时不渲染「当前没有需要处理的异常或待办」；SSR 保留对应 5xx/503。
- AC-2: `IncubatorShell` 不再把 overview 失败吞成 `null` 并显示 0 角标。
- AC-3: 文章/项目/书摘编辑与文章预览、名片页在主资源加载失败时走 `useApiFailure`，不渲染空白编辑器。
- AC-4: 新建文章的栏目/标签、新建项目的文章选项，以及孵化三池/任务列表加载失败时不显示「尚无/没有内容」空成功。
- AC-5: `apps/web/README.md` 记录上述后台加载失败语义；契约测试覆盖这些页面或共享 composable。

## Result

Verified and closed by the harness close command.

## Evidence

[20260815-admin-load-failures.json](../../verification/evidence/20260815-admin-load-failures.json)

Closed at 2026-08-15T16:32:48.466423+00:00.
