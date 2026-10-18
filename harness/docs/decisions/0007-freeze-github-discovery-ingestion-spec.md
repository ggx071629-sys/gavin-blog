---
id: decision-freeze-github-discovery-ingestion-spec
level: L2
summary: 已被外置决策取代的 GitHub 发现摄入冻结历史
load_when:
  - historical-architecture
  - task:20260807-github-discovery-ingestion
author: Gavin
---

# Decision 0007: Freeze GitHub discovery ingestion spec

## Status

Superseded on 2026-08-27 by [Externalize the retired GitHub incubator specs](20260827-externalize-retired-github-specs.md). The freeze rationale below remains historical; its resume and close instructions are no longer current for this task.

## Decision

将 `20260807-github-discovery-ingestion` 规格冻结在 2026-08-08 的实现与验收状态，等待已冻结的 `20260807-github-source-crawler` 恢复，并在具备真实跨仓库 E2E 条件后继续。

这是开发顺序选择，不是技术依赖结论。本地确定性测试替身仍可覆盖 GitHub REST、Webhook、Worker、迁移、契约和管理页面流程；冻结期间不继续补齐这些检查，也不得把现有 Harness 结构验证解释为应用验收完成。

冻结不是关闭。原始 spec 保留在 `harness/specs/active/`，目标、边界、验收条件与验证计划不得被静默改写。当前已知缺口至少包括 GitHub 管理端 Playwright E2E，以及限流／超时、结果截断、部分失败 checkpoint 和 Worker 崩溃恢复的充分自动化证据。

后续恢复时，应先重新核对工作树与冻结基线，补齐本地确定性验收；真实“机器画像 → crawler → sources → Webhook → my_blog”链路则与 source crawler 一起验证。所有适用检查通过后，两个 spec 仍须分别按正常 close 流程关闭。

## Consequences

- ingestion 与 source crawler 均保持 active 目录中的冻结状态，不宣称完成。
- 新的 UI 重构或其他任务不得静默吸收、修改或删除当前 GitHub 摄入边界。
- 冻结期间发现的新需求必须建立独立 task/spec，或明确记录为恢复后的验收补充。
- 现有未提交应用实现仍需独立保护；本决策提交不等同于提交或验收该实现。

## Lifecycle amendment

Decision 0008 将手工冻结升级为受门禁约束的生命周期。继续本任务的本地或跨仓库验收前必须先显式执行 Harness resume 命令；冻结目标、缺口和验收边界保持不变。
