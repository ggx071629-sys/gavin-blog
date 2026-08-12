---
id: spec-20260811-audit-plan-retry-idempotency
level: L1
summary: 修复同一资料修订在终态审计计划后无法重新准备的幂等冲突
load_when:
  - task:20260811-audit-plan-retry-idempotency
author: Codex
task_id: 20260811-audit-plan-retry-idempotency
status: active
state_history:
---

# Context

审计计划项的唯一幂等键当前只包含资料 ID、修订 ID 和检索模式。旧计划进入 `confirmed`、`failed` 或 `stale` 等终态后，创建逻辑不会复用旧项，却仍生成相同唯一键，导致 SQLite `UNIQUE constraint failed` 并向前端返回 500。登录前的 session 探测 401 与该失败无关。

# Goal

将普通审计计划项的幂等键限定在计划作用域，使相同资料修订和模式在旧计划终止后可以重新准备；仍在 `planning`/`ready` 状态的相同计划项继续按现有规则复用。

# Non-goals

不修改数据库表或迁移；不改变 Session/CSRF 认证；不自动重新提交第三方 LLM；不改变审计计划状态机、外发确认或重新判定接口；不清理历史计划数据。

# Acceptance criteria

- 同一资料修订和模式在旧计划项进入终态后再次创建计划返回 202，不触发唯一键冲突。
- 新计划项拥有新的计划作用域幂等键，并创建独立本地规划任务。
- 相同资料修订仍存在 `planning`/`ready` 计划项时，继续复用现有计划项。
- API 认证、外发确认及其他 LLM 审计行为保持不变。

# Risks

若幂等键完全随机化，会削弱重复请求保护；若继续使用跨计划全局键，则终态重试仍会失败。修复只增加计划 ID 作为作用域，不改变现有未完成项查询条件。

# Verification plan

先增加终态计划后再次准备的 API 回归测试并确认旧实现失败；实施最小键格式修改；运行 LLM 审计、Worker、提示词专项测试和 Ruff，再运行完整 API 回归及 Harness verify。
