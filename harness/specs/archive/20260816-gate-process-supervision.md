---
id: archive-20260816-gate-process-supervision
level: L2
summary: 让 task verify 的产品 gate 超时杀整棵进程树，并把子进程输出实时写到终端
load_when:
  - task:20260816-gate-process-supervision
author: Gavin
task_id: 20260816-gate-process-supervision
status: compressed
documentation_impact: required
documentation_targets:
  - harness/verification/README.md
documentation_reason: 门禁监督与超时杀树改变了 verify 的可观察执行合同，需要写进验证政策。
state_history:
---

# 20260816-gate-process-supervision

Deterministic compressed record. The original active spec remains in Git history.

## Goal

产品 gate 在独立进程组中运行；超时拆除整棵子孙进程并返回既有 timeout 失败形状；子进程输出边产生边写到 verify 终端，同时仍被采集进 evidence 摘要。

## Acceptance criteria

- AC-1: 监督启动的 gate 子进程在超时后整棵进程树不再存活；runner 返回 `failure.kind = timeout`，不再因残留管道而挂起。
- AC-2: gate 的标准输出在运行中写到 verify 进程的 stdout，并仍进入现有失败摘要与测试计数解析。
- AC-3: 非零退出、超时、执行错误的结构化 result 形状保持不变；Harness 测试覆盖监督启动与超时杀树。

## Result

Verified and closed by the harness close command.

## Evidence

[20260816-gate-process-supervision.json](../../verification/evidence/20260816-gate-process-supervision.json)

Closed at 2026-08-15T16:48:46.029161+00:00.
