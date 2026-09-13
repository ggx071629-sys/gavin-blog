import type { AssistantAdminSnapshot, AssistantFactStatus, AssistantIndexTaskList, AssistantOperation } from '~/types/api'

const factStatuses = new Set<AssistantFactStatus>(['healthy', 'degraded', 'blocked', 'disabled', 'stale', 'unknown'])
const operationStatuses = new Set(['pending', 'running', 'waiting', 'catch_up', 'ready_to_switch', 'switch_pending', 'switched', 'failed', 'abandoned'])

const object = (value: unknown, name: string): Record<string, unknown> => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`${name} contract is invalid`)
  return value as Record<string, unknown>
}
const exact = (row: Record<string, unknown>, allowed: readonly string[], name: string) => {
  const extras = Object.keys(row).filter(key => !allowed.includes(key))
  if (extras.length) throw new Error(`${name} contract has unknown fields`)
}
const text = (value: unknown, name: string) => {
  if (typeof value !== 'string') throw new Error(`${name} contract is invalid`)
  return value
}
const number = (value: unknown, name: string) => {
  if (typeof value !== 'number' || !Number.isSafeInteger(value)) throw new Error(`${name} contract is invalid`)
  return value
}

export const parseAssistantOperation = (value: unknown): AssistantOperation => {
  const row = object(value, 'operation')
  exact(row, ['operation_id', 'kind', 'status', 'version', 'generation_id', 'previous_generation_id', 'source_cursor', 'outbox_high_water', 'safe_error_code', 'message', 'created_at', 'updated_at', 'terminal_at'], 'operation')
  if (!operationStatuses.has(text(row.status, 'operation.status'))) throw new Error('operation.status contract is invalid')
  number(row.version, 'operation.version')
  text(row.operation_id, 'operation.id')
  text(row.kind, 'operation.kind')
  return row as unknown as AssistantOperation
}

export const parseAssistantSnapshot = (value: unknown): AssistantAdminSnapshot => {
  const row = object(value, 'snapshot')
  exact(row, ['status', 'observed_at', 'runtime_observed_at', 'content_observed_at', 'deployment', 'availability', 'readiness', 'cleanup', 'restore', 'qdrant', 'chat_provider', 'embedding_provider', 'worker', 'manifest', 'queue', 'operation', 'budgets', 'daily_activity'], 'snapshot')
  if (!['complete', 'partial'].includes(text(row.status, 'snapshot.status'))) throw new Error('snapshot.status contract is invalid')
  text(row.observed_at, 'snapshot.observed_at')
  const deployment = object(row.deployment, 'deployment')
  exact(deployment, ['api_capability', 'single_api_owner', 'launcher_source', 'launcher_mounted'], 'deployment')
  if (typeof deployment.api_capability !== 'boolean' || typeof deployment.single_api_owner !== 'boolean') throw new Error('deployment contract is invalid')
  const availability = object(row.availability, 'availability')
  exact(availability, ['requested_state', 'effective_state', 'version', 'operational_epoch', 'blocked_reason', 'switch_pending_operation_id', 'switch_target_generation_id', 'updated_at', 'draining_attempts'], 'availability')
  number(availability.version, 'availability.version')
  number(availability.operational_epoch, 'availability.epoch')
  for (const key of ['readiness', 'cleanup', 'restore', 'qdrant', 'chat_provider', 'embedding_provider', 'worker']) {
    const fact = object(row[key], key)
    exact(fact, ['status', 'reason_code', 'observed_at', 'freshness_seconds', 'stale'], key)
    if (!factStatuses.has(text(fact.status, `${key}.status`) as AssistantFactStatus) || typeof fact.stale !== 'boolean') throw new Error(`${key} contract is invalid`)
  }
  if (!Array.isArray(row.budgets) || row.budgets.length !== 3) throw new Error('budgets contract is invalid')
  row.budgets.forEach((item, index) => {
    const budget = object(item, `budget.${index}`)
    exact(budget, ['kind', 'beijing_date', 'cap_micro_cny', 'settled_micro_cny', 'reserved_micro_cny', 'remaining_micro_cny', 'overage_micro_cny', 'circuit_open', 'calls', 'input_tokens', 'output_tokens', 'usage_known', 'observed_at', 'authority'], `budget.${index}`)
    text(budget.kind, `budget.${index}.kind`)
    text(budget.authority, `budget.${index}.authority`)
  })
  if (row.operation !== null) parseAssistantOperation(row.operation)
  object(row.queue, 'queue')
  object(row.manifest, 'manifest')
  const activity = object(row.daily_activity, 'daily_activity')
  for (const key of ['feedback_helpful', 'feedback_unhelpful']) {
    if (activity[key] !== undefined && activity[key] !== null && (!Number.isInteger(activity[key]) || Number(activity[key]) < 0)) throw new Error('feedback contract is invalid')
  }
  if (activity.stages !== undefined) {
    if (!Array.isArray(activity.stages)) throw new Error('stage contract is invalid')
    for (const value of activity.stages) {
      const stage = object(value, 'stage')
      exact(stage, ['stage', 'count', 'latency_ms_min', 'latency_ms_max'], 'stage')
      if (!Number.isInteger(stage.count) || Number(stage.count) < 0) throw new Error('stage count is invalid')
      if (!['checking', 'retrieving', 'evidence_gate', 'composing', 'validating'].includes(String(stage.stage))) throw new Error('stage contract is invalid')
      for (const key of ['count', 'latency_ms_min', 'latency_ms_max']) {
        if (stage[key] !== null && (!Number.isInteger(stage[key]) || Number(stage[key]) < 0)) throw new Error('stage metric is invalid')
      }
    }
  }
  return row as unknown as AssistantAdminSnapshot
}

export const parseAssistantTasks = (value: unknown): AssistantIndexTaskList => {
  const row = object(value, 'task list')
  if (!Array.isArray(row.items)) throw new Error('task list contract is invalid')
  number(row.limit, 'task list limit')
  number(row.offset, 'task list offset')
  row.items.forEach((item, index) => {
    const task = object(item, `task.${index}`)
    exact(task, ['id', 'source_type', 'source_id', 'target_version', 'pipeline_version', 'operation', 'status', 'version', 'attempt_count', 'safe_error_code', 'message', 'parent_task_id', 'operator_authorized', 'created_at', 'updated_at'], `task.${index}`)
    number(task.id, `task.${index}.id`)
    number(task.version, `task.${index}.version`)
    text(task.status, `task.${index}.status`)
    text(task.operation, `task.${index}.operation`)
    if (task.message !== null && typeof task.message !== 'string') throw new Error(`task.${index}.message contract is invalid`)
  })
  return row as unknown as AssistantIndexTaskList
}

export const assistantOperationIsTerminal = (status: string) => ['switched', 'failed', 'abandoned'].includes(status)

export const assistantFactLabel: Record<AssistantFactStatus, string> = {
  healthy: '正常', degraded: '降级', blocked: '阻塞', disabled: '关闭', stale: '已过期', unknown: '未知',
}
