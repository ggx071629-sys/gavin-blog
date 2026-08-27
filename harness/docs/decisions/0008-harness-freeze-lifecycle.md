---
id: decision-harness-freeze-lifecycle
level: L1
summary: 将人工冻结与恢复固化为受门禁约束且可审计的 Harness 生命周期
load_when:
  - spec-freeze
  - spec-resume
  - architecture-decision
author: Gavin
---

# Decision 0008: Harness freeze lifecycle

## Status

Accepted.

## Decision

Harness 将冻结定义为 active spec 的可选人工暂停分支：`active → frozen → active`。冻结不是正常生命周期的必经阶段，不是关闭，也不代表项目全局质量失败。冻结 spec 保留在 `specs/active/`，但索引与统计必须将其和正在推进的 active spec 分开。

状态转换只能使用确定性 `freeze` 与 `resume` 命令，原因必填，所有事件追加记录操作、UTC 时间与原因。不得因测试失败、等待依赖或外部条件变化自动冻结或恢复；不得提供绕过冻结直接验证或关闭的强制开关。冻结不会阻止其他独立 spec，但新任务不得静默接管或改写冻结范围。

冻结时对 `Goal`、`Non-goals`、`Acceptance criteria` 与 `Verification plan` 建立 SHA-256 摘要。冻结期间可以维护备注、阻塞信息和证据，核心契约若需修改则必须先恢复。无 task ID 的全局门禁只校验冻结状态和摘要合法性；任务级 verify 与 close 必须拒绝冻结任务。

现有 `20260807-github-source-crawler` 与 `20260807-github-discovery-ingestion` 迁移到该生命周期并保持冻结。由于原冻结时没有摘要，迁移事件必须标记 `baseline: migration`，摘要只证明迁移后的完整性，不得伪称能够证明此前内容未变。既有 Harness-only passed evidence 是旧语义下的历史记录，不构成冻结任务完成或可关闭的声明。

## Consequences

- 暂停状态成为可执行的不变量，而不再只是自由文本标签。
- 长期冻结不会永久拖红 release 门禁，也不会阻塞无关工作。
- 恢复是继续验证、调整契约或关闭前的显式审计节点。
- 完整状态历史随原始 spec 保存在 Git 历史中，并在压缩归档中继续保留。

## Task-specific follow-up

`20260807-github-source-crawler` 与 `20260807-github-discovery-ingestion` 在 2026-08-27 随已退役知识孵化边界迁入独立只读归档，不再保留在博客主项目的开放规格列表，也不能再通过 `resume` 恢复。该例外由 [Externalize the retired GitHub incubator specs](20260827-externalize-retired-github-specs.md) 明确记录；它不改变其他任务的通用 freeze/resume 生命周期。
