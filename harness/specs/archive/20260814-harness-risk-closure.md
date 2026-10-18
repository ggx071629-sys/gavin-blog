---
id: archive-20260814-harness-risk-closure
level: L2
summary: 让变更覆盖只接受验证过最后风险修改的 evidence，并封闭控制面路径漏口
load_when:
  - task:20260814-harness-risk-closure
author: Codex
task_id: 20260814-harness-risk-closure
status: compressed
documentation_impact: required
documentation_targets:
  - harness/verification/README.md
documentation_reason: change coverage 的可信时序与风险边界属于长期验证合同，必须同步到权威验证政策
state_history:
---

# 20260814-harness-risk-closure

Deterministic compressed record. The original active spec remains in Git history.

## Goal

让 change coverage 确定性证明当前比较区间中的最后一次风险修改已包含在至少一份有效 schema v2 产品 evidence 的验证树中，并把完整控制面与项目实现边界纳入风险识别；evidence 之后仅允许该 task 的确定性 close 产物与生成索引。

## Acceptance criteria

- AC-1: 有效 evidence source 之后出现任一风险路径修改时，`change-check` 必须失败并列出未覆盖路径；旧 evidence 不再覆盖后续风险代码。
- AC-2: evidence source 之后只包含同 task 的 active spec 删除、archive、schema v2 evidence、`spec.completed` event 与确定性生成索引时，change coverage 继续通过。
- AC-3: 多 task 区间只要存在一份有效 evidence 覆盖最后风险修改即可通过；较旧 task 保留审计价值但不能掩盖时序缺口。
- AC-4: 风险识别覆盖完整 `.github/`、`apps/`、`packages/`、`scripts/`、`harness/`，以及 `AGENTS.md`、`.gitattributes`、`.gitignore`、`package.json`、`package-lock.json`。
- AC-5: 回归测试覆盖后置风险修改、确定性 close 例外、错误 task close 产物、扩展风险路径与可操作失败摘要。
- AC-6: 权威验证政策说明风险闭包、允许的后验证产物和本地 release coverage skip 边界。
- AC-7: release profile 与相对 `origin/main` 的 change coverage 完整通过并生成当前 schema v2 evidence。

## Result

Verified and closed by the harness close command.

## Evidence

[20260814-harness-risk-closure.json](../../verification/evidence/20260814-harness-risk-closure.json)

Closed at 2026-08-14T01:33:35.301702+00:00.
