---
id: decision-freeze-github-source-crawler-spec
level: L2
summary: 已被外置决策取代的 GitHub 爬虫冻结历史
load_when:
  - historical-architecture
  - task:20260807-github-source-crawler
author: Gavin
---

# Decision 0006: Freeze GitHub source crawler spec

## Status

Superseded on 2026-08-27 by [Externalize the retired GitHub incubator specs](20260827-externalize-retired-github-specs.md). The freeze rationale below remains historical; its resume and close instructions are no longer current for this task.

## Decision

将 `20260807-github-source-crawler` 规格冻结在 2026-08-07 的实现和验收基线上。冻结不是关闭：原始 spec 保留在 `harness/specs/active/`，其目标、边界、验收条件和验证计划不得被后续项目改动静默改写。

在 my_blog 完成域名部署并具备真实 profile/Webhook E2E 条件前，新的爬虫、博客或跨栈改动必须创建新的 task/spec，或明确标注为与该冻结基线无关的独立维护任务。不得通过修改冻结 spec 来吸收新的需求、改变验收口径或掩盖未完成的跨仓库验证。

冻结不会阻止后续验证。公网可访问的机器画像接口和 Webhook 配置完成后，可以直接使用这份冻结 spec 执行真实的“画像读取 → 爬虫 → sources → Webhook → my_blog 消费端”E2E，并把证据归档到 Harness。E2E 通过后可以按正常 close 流程关闭 spec。

只有当后续发现目标、边界或验收口径需要改变时，才需要由管理员明确要求解冻；此时应先记录变更原因，再修改 spec 或创建替代 spec。

## Consequences

- 当前 Draft PR、离线测试证据和未完成的真实 E2E 缺口保持可审计。
- 未来项目迭代不会污染本次爬虫验收基线。
- 新 task 需要显式说明是否依赖冻结 spec，以及是否会改变其未完成验收项。

## Lifecycle amendment

Decision 0008 将手工冻结升级为受门禁约束的生命周期。恢复真实 E2E 时必须先显式执行 Harness resume 命令；原文中“直接验证并关闭”和“只有改变范围才需要解冻”的操作约定由 Decision 0008 取代，冻结目标和验收边界本身不变。
