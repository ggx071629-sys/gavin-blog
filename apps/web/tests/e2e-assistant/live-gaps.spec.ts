import { expect, test } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

test('management renders identity costs current errors stale diagnostics and running state', async ({ page }) => {
  await page.goto('/admin/login')
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  // These are UI contract fixtures, not evidence of actual indexing or billing.
  await page.route('**/api/v1/admin/assistant', async route => {
    const response = await route.fetch()
    const snapshot = await response.json()
    snapshot.daily_activity.latency_ms_min = null
    snapshot.daily_activity.latency_ms_max = null
    snapshot.worker.stale = true
    snapshot.worker.status = 'unknown'
    snapshot.operation = {
      operation_id: 'ui-running', kind: 'rebuild', status: 'running', version: 1,
      generation_id: 2, previous_generation_id: 1, source_cursor: null,
      outbox_high_water: null, safe_error_code: null, message: null,
      created_at: snapshot.observed_at, updated_at: snapshot.observed_at, terminal_at: null,
    }
    await route.fulfill({ response, json: snapshot })
  })
  await page.route('**/api/v1/admin/assistant/management', async route => {
    const response = await route.fetch()
    const body = await response.json()
    body.usage_known = true
    body.scope_costs = [
      { scope: 'admin', kind: 'chat', settled_micro_cny: 1000, reserved_micro_cny: 0 },
      { scope: 'public', kind: 'chat', settled_micro_cny: 2000, reserved_micro_cny: 0 },
    ]
    await route.fulfill({ response, json: body })
  })
  await page.route('**/api/v1/admin/assistant/sync?*', route => route.fulfill({ json: {
    items: [{ id: 'ui-failed', title: '当前失败条目', source_type: 'article', status: 'failed',
      updated_at: '2026-09-13T00:00:00Z', message: '供应商调用结果未确认，请核对账单。',
      safe_error_code: 'provider_result_unknown', provider_state: 'unknown',
      resolved_by_current_index: false, current_revision: true, version: 1 }],
    total: 1, offset: 0, limit: 10,
  } }))
  await page.goto('/admin/assistant')
  await expectHydrated(page)
  await expect(page.getByText('今日回答耗时 未确认–未确认 ms')).toBeVisible()
  await page.getByRole('button', { name: /费用明细/ }).click()
  await expect(page.getByRole('dialog')).toContainText('后台试问')
  await expect(page.getByRole('dialog')).toContainText('访客问答')
  await page.getByRole('button', { name: '关闭弹窗' }).click()
  await page.getByRole('button', { name: /查看内容/ }).click()
  await expect(page.getByRole('dialog')).toContainText('供应商调用结果未确认，请核对账单。')
  await expect(page.getByRole('button', { name: '重试此内容同步' })).toHaveCount(0)
  await page.getByRole('link', { name: '查看诊断', exact: true }).click()
  await expect(page.getByRole('dialog')).toContainText('（观察已过期）')
  await expect(page.getByRole('dialog')).toContainText('当前操作：重建中')
  await expect(page.getByRole('button', { name: '重建公开知识索引', exact: true })).toBeDisabled()
  await expect(page.getByRole('button', { name: '切换到新索引', exact: true })).toHaveCount(0)
})
