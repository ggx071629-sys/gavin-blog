---
id: spec-20260814-harness-risk-closure
level: L1
summary: 让变更覆盖只接受验证过最后风险修改的 evidence，并封闭控制面路径漏口
load_when:
  - task:20260814-harness-risk-closure
author: Codex
task_id: 20260814-harness-risk-closure
status: active
verification_profile: release
documentation_impact: required
documentation_targets:
  - harness/verification/README.md
documentation_reason: change coverage 的可信时序与风险边界属于长期验证合同，必须同步到权威验证政策
state_history:
---

# Context

当前 `change-check` 只要求比较区间内存在至少一份有效 task archive/evidence，并验证 evidence source commit 可从 head 到达。它不检查 evidence 之后是否又出现风险修改，因此长期 PR 可以在完成一次 task 后追加未经该 evidence 验证的应用或控制面改动，旧 evidence 仍可能覆盖整个区间。风险白名单同时遗漏 `AGENTS.md`、大部分 Harness 政策、遥测、演进和非 contracts package 路径。

# Goal

让 change coverage 确定性证明当前比较区间中的最后一次风险修改已包含在至少一份有效 schema v2 产品 evidence 的验证树中，并把完整控制面与项目实现边界纳入风险识别；evidence 之后仅允许该 task 的确定性 close 产物与生成索引。

# Non-goals

- 不合并 Draft PR，不改变仓库可见性，不虚构 GitHub Free 私有仓库的 branch protection。
- 不建立外部策略仓库、CODEOWNERS 审批人或组织级 ruleset。
- 不自动把历史 schema v1/invalid evidence 升级为当前保证等级。
- 不改变产品行为、部署拓扑或 telemetry 的人类确认边界。

# Acceptance criteria

- AC-1: 有效 evidence source 之后出现任一风险路径修改时，`change-check` 必须失败并列出未覆盖路径；旧 evidence 不再覆盖后续风险代码。
- AC-2: evidence source 之后只包含同 task 的 active spec 删除、archive、schema v2 evidence、`spec.completed` event 与确定性生成索引时，change coverage 继续通过。
- AC-3: 多 task 区间只要存在一份有效 evidence 覆盖最后风险修改即可通过；较旧 task 保留审计价值但不能掩盖时序缺口。
- AC-4: 风险识别覆盖完整 `.github/`、`apps/`、`packages/`、`scripts/`、`harness/`，以及 `AGENTS.md`、`.gitattributes`、`.gitignore`、`package.json`、`package-lock.json`。
- AC-5: 回归测试覆盖后置风险修改、确定性 close 例外、错误 task close 产物、扩展风险路径与可操作失败摘要。
- AC-6: 权威验证政策说明风险闭包、允许的后验证产物和本地 release coverage skip 边界。
- AC-7: release profile 与相对 `origin/main` 的 change coverage 完整通过并生成当前 schema v2 evidence。

# Risks

- 将整个 Harness 纳入风险范围后，close 自身会产生验证提交之后的文件；例外必须精确到 task 路径，不能用宽泛目录排除。
- PR 基线变化可能把未包含在本地 evidence source 的新风险修改带入 merge commit；严格失败是预期行为，需要重新基于最新树验证。
- 当前 PR 比较区间很长，修复必须保持对多 task 串行关闭的兼容。

# Verification plan

- release => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7
