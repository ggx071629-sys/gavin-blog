---
id: decision-verification-cost-rightsize
level: L1
summary: 按路径风险拆分控制面验证下限，并禁止包门禁独占多条验收标准
load_when:
  - harness-change
  - verification
  - architecture-decision
author: Codex
---

# Decision: verification cost right-size

## Status

Accepted.

## Context

原先一条 `release-control` 把 CI、脚本、Harness 工具、workflow、SDD 与 harness 测试都抬到完整 `release`。控制面小改动因此默认支付产品发布税，verification plan 也习惯把全部 AC 映射到 `release`。`criteria_results` 只证明声明映射执行过。Evolution 已能引用本地失败 run，但 verify 失败现场不提示命令。

## Decision

- `harness-docs` 覆盖 `harness/docs/`、`harness/workflows/`、`harness/evolution/`，最低 gate 为 `harness-integrity`。
- `harness-control` 覆盖 `harness/tools/`、`harness/verification/checks/`、`harness/verification/tests/`、`harness/specs/_sdd/`，最低 gate 为 `harness-tests` 与 `harness-integrity`。
- `release-control` 只覆盖 `.github/`、`scripts/`、`AGENTS.md`、`harness/config.toml` 以及根锁/忽略文件，最低 gate 仍为 `release`。
- API、Web、跨栈契约路由不变。spec 仍只能增加不能降低推导下限。
- 带 `subsumption_contract` 的 gate 是包门禁。超过一条 AC 时，每条 AC 必须至少映射一个叶子 gate；不能把全部 AC 只挂在同一个包门禁上。
- 计划额外选择不在风险下限内的包门禁时，active spec 必须提供非空单行 `verification_escalation`。
- `python -m tools.harness spec-lint [task_id]` 复用 verify 的合同与映射检查，不启动产品 gate。
- task verify 失败且本地 JSONL 已有同一 task 至少两个 failed run 时，打印可复制的 `emit-event verification.repeated_failure` 命令。提示不写文件、不改 gate、不改变退出码。

## Consequences

- 只改 Harness 文档或控制面代码的任务可以在分钟级关闭，不必默认跑 Lighthouse 与完整 E2E。
- 改 CI、发布脚本、锁文件或 `config.toml` 仍然支付完整 release。
- 多 AC 的 `release => AC-1...AC-N` 申报路径会被前置检查拒绝。
- telemetry 仍不得影响行为；重复失败是否进入 Evolution 仍由人确认。
