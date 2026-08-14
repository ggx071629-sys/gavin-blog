---
id: archive-20260814-verification-cost-rightsize
level: L2
summary: 按改动风险拆分控制面验证下限，并禁止用包门禁独占多条验收标准
load_when:
  - task:20260814-verification-cost-rightsize
author: Gavin
task_id: 20260814-verification-cost-rightsize
status: compressed
documentation_impact: required
documentation_targets:
  - harness/docs/decisions/20260814-verification-cost-rightsize.md
  - harness/specs/_sdd/README.md
  - harness/specs/_sdd/template.md
  - harness/verification/README.md
  - harness/workflows/specify.md
  - harness/workflows/verify.md
documentation_reason: 风险路由分档、包门禁映射规则和失败现场 Evolution 提示会改变长期验证合同与日常 specify/verify 流程
state_history:
---

# 20260814-verification-cost-rightsize

Deterministic compressed record. The original active spec remains in Git history.

## Goal

把验证下限调回与路径风险匹配：只改控制面文档或 harness 可执行代码时，不再默认要求完整 `release`；多条 AC 不能只挂在带 subsumption 合同的包门禁上；同一 task 连续失败时，verify 打印已有的 `emit-event` 命令且不自动写 Evolution 文件。

## Acceptance criteria

- AC-1: `config.toml` 将原 `release-control` 拆为 `harness-docs`、`harness-control` 与收窄后的 `release-control`。仅改 `harness/tools/` 的已提交路径推导出 `harness-tests` 与 `harness-integrity`，不推导 `release`。
- AC-2: 仅改 `harness/docs/`、`harness/workflows/` 或 `harness/evolution/` 的已提交路径只推导 `harness-integrity`。
- AC-3: 改 `.github/`、`scripts/`、`harness/config.toml`、`AGENTS.md` 或根锁/忽略文件的已提交路径仍推导 `release`。
- AC-4: 超过一条 AC 且全部只映射到同一个带 `subsumption_contract` 的包门禁时，task verify 在创建隔离 worktree 或启动产品 gate 前失败，且不产生可关闭的 passed evidence。
- AC-5: 每条 AC 至少映射一个叶子 gate 时可以通过映射检查；若计划额外选择不在风险下限内的包门禁，必须提供非空单行 `verification_escalation`，否则同样在产品 gate 前失败。
- AC-6: `python -m tools.harness spec-lint <task_id>` 复用与 verify 相同的映射与风险下限检查，不启动产品 gate。task verify 失败且本地 JSONL 已有同一 task 至少两个 failed run 时，打印可复制的 `emit-event verification.repeated_failure` 命令；该提示不写 event 或 proposal。
- AC-7: 现有 Harness 单测与完整性检查保持通过；本任务因修改 `harness/config.toml` 仍以完整 `release` 作为产品证明，并写出当前 schema v2 evidence。

## Result

Verified and closed by the harness close command.

## Evidence

[20260814-verification-cost-rightsize.json](../../verification/evidence/20260814-verification-cost-rightsize.json)

Closed at 2026-08-14T12:22:27.900174+00:00.
