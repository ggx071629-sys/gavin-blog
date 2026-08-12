---
id: archive-20260812-harness-run-telemetry
level: L2
summary: 为任务验证与发布门禁建立本地追加式运行观测和确定性摘要
load_when:
  - task:20260812-harness-run-telemetry
author: Codex
task_id: 20260812-harness-run-telemetry
status: compressed
documentation_impact: required
documentation_targets:
  - harness/telemetry/README.md
  - harness/telemetry/schema/README.md
documentation_reason: 运行事件的字段、隐私边界、失败语义和摘要口径必须成为长期可复查的观测合同
state_history:
---

# 20260812-harness-run-telemetry

Deterministic compressed record. The original active spec remains in Git history.

## Goal

让 task verify 与 `quality:release` 以不影响门禁结果的方式追加结构化本地事件，并提供验证与确定性摘要命令，使运行状态、耗时和失败类别可复算、可人工回顾。

## Acceptance criteria

- AC-1: task verify 完成后追加 `task.verification` 事件，包含状态、总耗时、check/test 计数、失败类别、profile、source commit 与隔离清理状态，但不包含原始日志或命令。
- AC-2: `quality:release` 为每个执行阶段追加 `release.stage`，并为成功或提前失败追加一个 `release.run`；事件包含随机 run ID、阶段、状态、耗时、退出码和 change coverage 模式。
- AC-3: telemetry 写入异常只能产生有限告警，不能把原本通过的验证改成失败，也不能掩盖原始 gate 失败。
- AC-4: `python -m tools.harness telemetry-summary [--json]` 验证本地 JSONL，并确定性计算事件数、状态数、按 kind/stage 聚合以及 duration 的 count/P50/P95/max；无数据时返回合法空摘要。
- AC-5: 文档明确事件字段、隐私边界、百分位口径、原始数据不提交以及人工 retrospective 才能进入 Evolution。

## Result

Verified and closed by the harness close command.

## Evidence

[20260812-harness-run-telemetry.json](../../verification/evidence/20260812-harness-run-telemetry.json)

Closed at 2026-08-12T09:04:21.922477+00:00.
