import type { AssistantAdminSnapshot, AssistantIndexTask } from '~/types/api'
import { closeAnswerCitations } from './assistant/citations'

export interface TotalBudget {
  beijing_date: string
  cap_micro_cny: number
  ceiling_micro_cny: number
  version: number
  settled_micro_cny: number
  reserved_micro_cny: number
  remaining_micro_cny: number
  question_headroom_micro_cny: number
  chat_headroom_micro_cny: number
  restore_locked: boolean
}
export interface AssistantManagement {
  budget: TotalBudget
  usage_known: boolean
  trial_available: boolean
  trial_stopped: boolean
  scope_costs: { scope: string, kind: string, settled_micro_cny: number, reserved_micro_cny: number }[]
}
export interface SyncTask extends AssistantIndexTask {
  title: string
  public_path: string | null
  current_revision: boolean
  provider_state: string | null
  resolved_by_current_index?: boolean
}
export interface SyncTasks { items: SyncTask[], total: number, limit: number, offset: number }
export const money = (value: number | null | undefined) => value == null ? '暂不可确认' : `¥${(value / 1000000).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 6 })}`
export const amountToMicro = (value: string): number | null => {
  if (!/^(0|[1-9]\d{0,8})(\.\d{1,6})?$/.test(value.trim())) return null
  const [whole = '0', fraction = ''] = value.trim().split('.')
  const result = Number(whole) * 1000000 + Number(fraction.padEnd(6, '0'))
  return Number.isSafeInteger(result) ? result : null
}
export const budgetLabel: Record<string, string> = { chat: '回答生成', query_embedding: '问题检索', index_embedding: '内容同步' }
export const syncLabel = (task: SyncTask) => {
  if (task.status === 'failed' && task.resolved_by_current_index === true) return '历史失败（当前已收录）'
  if (task.provider_state === 'deferred') return '等待预算'
  if (task.status === 'succeeded') return task.current_revision ? '此修订已处理' : '历史任务已处理'
  return ({ pending: '待同步', leased: '同步中', failed: '同步失败' })[task.status] || task.status
}
export const canRetry = (task: SyncTask) => task.status === 'failed' && task.resolved_by_current_index !== true && !['unknown', 'sending', 'succeeded'].includes(task.provider_state || '') && !['provider_result_unknown', 'index_embedding_unknown'].includes(task.safe_error_code || '')
export const serviceHeadline = (snapshot: AssistantAdminSnapshot, management: AssistantManagement | null, stale: boolean) => {
  if (stale) return '当前状态待确认'
  if (snapshot.availability.requested_state === 'disabled' && snapshot.availability.effective_state !== 'blocked') return '已关闭对外问答'
  if (snapshot.availability.effective_state !== 'enabled') return '暂时无法开放'
  const budget = management?.budget
  const chat = snapshot.budgets?.find(item => item.kind === 'chat')
  if (chat?.circuit_open) return '费用计量异常，问答已暂停'
  if (budget?.restore_locked) return '恢复保护中，问答已暂停'
  if (budget && chat?.remaining_micro_cny != null && chat.remaining_micro_cny < budget.chat_headroom_micro_cny) return '回答生成预算不足，问答已暂停'
  if (budget && budget.remaining_micro_cny < budget.question_headroom_micro_cny) return '今日预算不足，问答已暂停'
  return '已向访客开放'
}
export interface TrialCitation { n: string, title: string, path: string, excerpt: string }
export function trialCitations(answer: string, citations: unknown, sources: unknown): TrialCitation[] {
  if (!Array.isArray(citations)) throw new Error('回答依据格式无效')
  const normalized = citations.map((item: Record<string, unknown>) => {
    const { excerpt, ...citation } = item
    if (typeof excerpt !== 'string' || excerpt.length > 1200) throw new Error('回答依据格式无效')
    return { excerpt, citation }
  })
  const closed = closeAnswerCitations(answer, normalized.map(item => item.citation), sources)
  if (!closed) throw new Error('回答与依据未通过校验')
  return closed.markers.map(({ n, citation }) => ({ n, title: citation.title, path: citation.path,
    excerpt: normalized.find(item => item.citation.n === n)!.excerpt }))
}
