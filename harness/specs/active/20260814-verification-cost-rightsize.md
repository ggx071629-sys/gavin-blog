---
id: spec-20260814-verification-cost-rightsize
level: L1
summary: 按改动风险拆分控制面验证下限，并禁止用包门禁独占多条验收标准
load_when:
  - task:20260814-verification-cost-rightsize
author: Gavin
task_id: 20260814-verification-cost-rightsize
status: active
verification_profile: release
verification_escalation: 本任务修改风险路由与 config.toml，推导下限即完整 release
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

# Context

当前 `release-control` 把 `.github/`、`scripts/`、`harness/tools/`、workflow、SDD、checks 与 harness 测试绑到同一个 `release` 下限。控制面小改动因此默认支付完整产品发布税，agent 也习惯把全部 AC 映射到 `release`。`criteria_results` 只证明声明映射执行过，不证明自然语言 AC 被单独测到。Evolution 已能从本地失败 run 生成 `verification.repeated_failure`，但 verify 失败现场不提示可复制命令，回路很少被使用。

# Goal

把验证下限调回与路径风险匹配：只改控制面文档或 harness 可执行代码时，不再默认要求完整 `release`；多条 AC 不能只挂在带 subsumption 合同的包门禁上；同一 task 连续失败时，verify 打印已有的 `emit-event` 命令且不自动写 Evolution 文件。

# Non-goals

- 不自动从 telemetry 创建 event、proposal，也不改变 gate 或 `AGENTS.md`。
- 不删除或改写历史 archive、evidence、event、proposal。
- 不降低 `apps/`、`packages/`、CI、锁文件或 `quality:release` 本身的门槛。
- 不解冻 GitHub crawler / discovery ingestion。
- 不把 workflow 做成 Python 调度器，不填空目录，不加新的 evidence schema。

# Acceptance criteria

- AC-1: `config.toml` 将原 `release-control` 拆为 `harness-docs`、`harness-control` 与收窄后的 `release-control`。仅改 `harness/tools/` 的已提交路径推导出 `harness-tests` 与 `harness-integrity`，不推导 `release`。
- AC-2: 仅改 `harness/docs/`、`harness/workflows/` 或 `harness/evolution/` 的已提交路径只推导 `harness-integrity`。
- AC-3: 改 `.github/`、`scripts/`、`harness/config.toml`、`AGENTS.md` 或根锁/忽略文件的已提交路径仍推导 `release`。
- AC-4: 超过一条 AC 且全部只映射到同一个带 `subsumption_contract` 的包门禁时，task verify 在创建隔离 worktree 或启动产品 gate 前失败，且不产生可关闭的 passed evidence。
- AC-5: 每条 AC 至少映射一个叶子 gate 时可以通过映射检查；若计划额外选择不在风险下限内的包门禁，必须提供非空单行 `verification_escalation`，否则同样在产品 gate 前失败。
- AC-6: `python -m tools.harness spec-lint <task_id>` 复用与 verify 相同的映射与风险下限检查，不启动产品 gate。task verify 失败且本地 JSONL 已有同一 task 至少两个 failed run 时，打印可复制的 `emit-event verification.repeated_failure` 命令；该提示不写 event 或 proposal。
- AC-7: 现有 Harness 单测与完整性检查保持通过；本任务因修改 `harness/config.toml` 仍以完整 `release` 作为产品证明，并写出当前 schema v2 evidence。

# Risks

- 分档过宽会让改 close/verify 语义的控制面缺陷只跑 harness 测试就关闭。
- 分档过窄会让这次修复无效，控制面改动继续默认 `release`。
- 映射规则若只看“是否出现过叶子 gate”而不要求每条 AC 都有叶子，包门禁独占问题会残留。
- 失败提示若写成文件或改返回码，会违反 telemetry 不得影响行为的边界。

# Verification plan

- harness-tests => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6
- harness-integrity => AC-1, AC-2, AC-3, AC-7
- release => AC-7
