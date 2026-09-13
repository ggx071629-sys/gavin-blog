---
id: archive-20260811-audit-plan-retry-idempotency
level: L2
summary: 修复同一资料修订在终态审计计划后无法重新准备的幂等冲突
load_when:
  - task:20260811-audit-plan-retry-idempotency
author: Codex
task_id: 20260811-audit-plan-retry-idempotency
status: compressed
state_history:
---

# 20260811-audit-plan-retry-idempotency

Deterministic compressed record. The original active spec remains in Git history.

## Goal

将普通审计计划项的幂等键限定在计划作用域，使相同资料修订和模式在旧计划终止后可以重新准备；仍在 `planning`/`ready` 状态的相同计划项继续按现有规则复用。

## Acceptance criteria

- 同一资料修订和模式在旧计划项进入终态后再次创建计划返回 202，不触发唯一键冲突。
- 新计划项拥有新的计划作用域幂等键，并创建独立本地规划任务。
- 相同资料修订仍存在 `planning`/`ready` 计划项时，继续复用现有计划项。
- API 认证、外发确认及其他 LLM 审计行为保持不变。

## Result

Verified and closed by the harness close command.

## Evidence

[20260811-audit-plan-retry-idempotency.json](../../verification/evidence/20260811-audit-plan-retry-idempotency.json)

Closed at 2026-08-12T02:22:47.659098+00:00.
