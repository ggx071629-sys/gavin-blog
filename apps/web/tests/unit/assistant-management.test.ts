import { describe, expect, it } from 'vitest'
import { amountToMicro, canRetry, serviceHeadline, syncLabel, trialCitations, type AssistantManagement, type SyncTask } from '../../utils/assistant-management'
import type { AssistantAdminSnapshot } from '../../types/api'

describe('assistant management contracts', () => {
  it('labels covered failures as history and never retries them', () => {
    const task = { status: 'failed', provider_state: null, safe_error_code: null } as SyncTask
    expect(canRetry(task)).toBe(true)
    expect(syncLabel(task)).toBe('同步失败')
    task.resolved_by_current_index = true
    expect(canRetry(task)).toBe(false)
    expect(syncLabel(task)).toBe('历史失败（当前已收录）')
    task.provider_state = 'unknown'
    expect(canRetry(task)).toBe(false)
    expect(task.status).toBe('failed')
  })
  it('never reports stale or budget blocked service as open', () => {
    const snapshot = { availability: { requested_state: 'enabled', effective_state: 'enabled' } } as AssistantAdminSnapshot
    const management = { budget: { remaining_micro_cny: 0, question_headroom_micro_cny: 1 } } as AssistantManagement
    expect(serviceHeadline(snapshot, management, true)).toBe('当前状态待确认')
    expect(serviceHeadline(snapshot, management, false)).toContain('已暂停')
    snapshot.availability.requested_state = 'disabled'
    snapshot.availability.effective_state = 'disabled'
    expect(serviceHeadline(snapshot, management, false)).toBe('已关闭对外问答')
  })
  it('uses exact decimal micro currency and rejects ambiguous values', () => {
    expect(amountToMicro('0.100001')).toBe(100001)
    expect(amountToMicro('2')).toBe(2000000)
    for (const input of ['1e3', '-1', '1.0000001', 'NaN', '', '.1', '01']) expect(amountToMicro(input)).toBeNull()
  })
  it('closes trial citations over safe public sources and bounded excerpts', () => {
    const citation = { n: '1', title: '公开文章', path: '/notes/2026/08/python-notes', excerpt: '公开证据' }
    const source = { n: '1', title: citation.title, path: citation.path }
    expect(trialCitations('回答[1]', [citation], [source])[0]?.excerpt).toBe('公开证据')
    expect(trialCitations('读取 `a[99]`。[1]', [citation], [source])).toHaveLength(1)
    expect(() => trialCitations('回答[2]', [citation], [source])).toThrow()
    expect(() => trialCitations('回答[1]', [{ ...citation, path: 'javascript:alert(1)' }], [source])).toThrow()
    expect(() => trialCitations('回答[1]', [{ ...citation, excerpt: 'x'.repeat(1201) }], [source])).toThrow()
  })
})
