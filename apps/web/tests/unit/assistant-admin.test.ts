import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { assistantOperationIsTerminal, parseAssistantSnapshot, parseAssistantTasks } from '../../utils/assistant-admin'

const fact = { status: 'unknown', reason_code: 'missing', observed_at: null, freshness_seconds: null, stale: true }
const snapshot = {
  status: 'partial', observed_at: '2026-08-30T00:00:00Z', runtime_observed_at: null, content_observed_at: '2026-08-30T00:00:00Z',
  deployment: { api_capability: false, single_api_owner: false, launcher_source: 'web_runtime_config', launcher_mounted: null },
  availability: { requested_state: 'disabled', effective_state: 'blocked', version: 0, operational_epoch: 0, blocked_reason: 'runtime_unavailable', switch_pending_operation_id: null, switch_target_generation_id: null, updated_at: null, draining_attempts: 0 },
  readiness: fact, cleanup: fact, restore: fact, qdrant: fact, chat_provider: fact, embedding_provider: fact, worker: fact,
  manifest: { generation_id: null, provider: null, model: null, model_version: null, dimension: null, pipeline_version: null, collection_present: null },
  queue: { pending: 0, leased: 0, succeeded: 0, failed: 0, latest_success_at: null }, operation: null,
  budgets: ['chat', 'query_embedding', 'index_embedding'].map(kind => ({ kind, beijing_date: '2026-08-30', cap_micro_cny: null, settled_micro_cny: null, reserved_micro_cny: null, remaining_micro_cny: null, overage_micro_cny: null, circuit_open: null, calls: null, input_tokens: null, output_tokens: null, usage_known: false, observed_at: null, authority: kind === 'index_embedding' ? 'content' : 'runtime' })),
  daily_activity: { accepted_questions: null, rate_limit_decisions: null, refusals: null, errors: null, security_events: null, latency_ms_min: null, latency_ms_max: null },
}

describe('assistant admin contract', () => {
  it('validates body-free feedback and observed stage metrics', () => {
    const activity = { ...snapshot.daily_activity, feedback_helpful: 2, feedback_unhelpful: 1, stages: [{ stage: 'composing', count: 2, latency_ms_min: 10, latency_ms_max: 20 }] }
    expect(parseAssistantSnapshot({ ...snapshot, daily_activity: activity }).daily_activity.feedback_helpful).toBe(2)
    expect(() => parseAssistantSnapshot({ ...snapshot, daily_activity: { ...activity, feedback_helpful: -1 } })).toThrow(/feedback/)
    expect(() => parseAssistantSnapshot({ ...snapshot, daily_activity: { ...activity, stages: [{ ...activity.stages[0], text: 'raw body' }] } })).toThrow(/stage/)
    expect(() => parseAssistantSnapshot({ ...snapshot, daily_activity: { ...activity, stages: [{ ...activity.stages[0], count: null }] } })).toThrow(/stage/)
  })
  it('strictly accepts the complete passive snapshot shape', () => {
    expect(parseAssistantSnapshot(snapshot).status).toBe('partial')
    expect(() => parseAssistantSnapshot({ ...snapshot, budgets: [] })).toThrow(/budgets contract/)
    expect(() => parseAssistantSnapshot({ ...snapshot, worker: { ...fact, status: 'green' } })).toThrow(/worker/)
  })

  it('rejects malformed task results and identifies terminal operations', () => {
    expect(parseAssistantTasks({ items: [], limit: 20, offset: 0 }).items).toEqual([])
    expect(() => parseAssistantTasks({ items: [{}], limit: 20, offset: 0 })).toThrow(/task.0/)
    expect(assistantOperationIsTerminal('switched')).toBe(true)
    expect(assistantOperationIsTerminal('ready_to_switch')).toBe(false)
  })

  it('keeps polling visibility-bound and renders errors as text', () => {
    const page = readFileSync(resolve(process.cwd(), 'pages/admin/assistant.vue'), 'utf8')
    const controller = readFileSync(resolve(process.cwd(), 'composables/useAssistantManagement.ts'), 'utf8')
    expect(controller).toContain("document.visibilityState === 'visible'")
    expect(controller).toContain('clearTimeout(timer)')
    expect(page).not.toContain('v-html')
    expect(controller).toContain('current !== revision')
  })
})
