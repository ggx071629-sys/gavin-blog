---
id: archive-20260813-telemetry-health-assessment
level: L2
summary: 为本地 Harness 遥测增加保守、只读且不触发行为的健康评估
load_when:
  - task:20260813-telemetry-health-assessment
author: Codex
task_id: 20260813-telemetry-health-assessment
status: compressed
documentation_impact: required
documentation_targets:
  - harness/telemetry/README.md
  - harness/evolution/policy.md
documentation_reason: 健康信号的统计语义及其不得自动驱动门禁或 Evolution 的边界属于长期控制面合同
state_history:
---

# 20260813-telemetry-health-assessment

Deterministic compressed record. The original active spec remains in Git history.

## Goal

增加只读 `telemetry-health` 命令，按配置化窗口和阈值评估连续失败与耗时回归，明确报告样本不足，并保持观察与决策隔离。

## Acceptance criteria

- AC-1: `python -m tools.harness telemetry-health [--json]` 只读现有 JSONL，按 task verification、release run 与稳定 release stage 序列输出确定性 assessment。
- AC-2: 每个序列至少区分 `no-data`、`insufficient-data`、`stable` 与 `signal`，且只有达到配置化最小样本后才能产生 failure 或 duration 信号。
- AC-3: failure 信号只基于最近连续失败数；duration 信号比较不重叠 baseline/recent 窗口的中位数比率，并处理零基线、缺失或非法 duration，避免除零和猜测。
- AC-4: 命令发现 signal 时仍返回成功，不写 telemetry/event/proposal，不输出动作建议；损坏 JSONL 仍按既有合同失败并定位文件与行号。
- AC-5: 配置与文档明确阈值、样本边界及“观察不能自动成为演化决定”的人工确认路径。

## Result

Verified and closed by the harness close command.

## Evidence

[20260813-telemetry-health-assessment.json](../../verification/evidence/20260813-telemetry-health-assessment.json)

Closed at 2026-08-13T13:16:38.467039+00:00.
