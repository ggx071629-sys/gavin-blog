import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { expectHydrated } from '../support/hydration'
import type { SyncTask } from '../../utils/assistant-management'

test('states', async ({ page }, info) => {
  test.setTimeout(180000)
  await page.goto('/admin/login')
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  await page.route('**/api/v1/admin/assistant/management', async route => {
    const response = await route.fetch()
    await route.fulfill({ response, json: { ...await response.json(), trial_available: true } })
  })
  const state = { pending: false, failRestore: false, failClear: false, answer: false, posts: 0 }
  const session = { session_id: 'isolated-trial-session', created_at: '2026-09-10T00:00:00Z', idle_expires_at: '2026-09-10T00:30:00Z', absolute_expires_at: '2026-09-10T04:00:00Z', policy: { question_max_chars: 2000, session_idle_seconds: 1800, session_absolute_seconds: 14400, body_retention_seconds: 1800 } }
  const unavailable = { error: { code: 'assistant_not_ready', message: '管理试问暂不可用' } }
  let release = () => {}
  const held = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/v1/admin/assistant/trial/**', async route => {
    const request = route.request()
    const path = new URL(request.url()).pathname
    if (path.endsWith('/sessions')) return route.fulfill({ json: { session_id: session.session_id, csrf_token: 'isolated-test', idle_expires_at: session.idle_expires_at, absolute_expires_at: session.absolute_expires_at, policy: session.policy } })
    if (path.endsWith('/questions')) {
      state.posts++; state.pending = true
      await held
      return route.abort().catch(() => {})
    }
    if (request.method() === 'DELETE') {
      if (state.failClear) return route.fulfill({ status: 503, json: unavailable })
      state.answer = false; state.pending = false
      return route.fulfill({ status: 204 })
    }
    if (state.failRestore) return route.fulfill({ status: 503, json: unavailable })
    return route.fulfill({ json: { ...session, turns: state.answer ? [{ turn_id: 'held-turn', created_at: session.created_at, status: 'answered', code: null, question: '中断后的问题', answer: '已恢复的回答。', message: null, cost_micro_cny: 101, citations: [], sources: [], body_available: true }] : [], active_turn: state.pending ? { turn_id: 'held-turn', question: '中断后的问题', created_at: session.created_at, stage: 'composing' } : null } })
  })
  await page.goto('/admin/assistant?view=test')
  await expectHydrated(page)
  const trial = page.locator('.am-trial')
  await page.getByLabel('你的问题').fill('中断后的问题')
  await page.getByRole('button', { name: '发送问题' }).click()
  await expect.poll(() => state.posts).toBe(1)
  await expect(page.getByRole('button', { name: '停止接收' })).toBeVisible()
  await page.getByRole('button', { name: '停止接收' }).click()
  release()
  await expect(trial.getByRole('status')).toContainText('后台调用可能仍在处理和计费')
  await expect(page.getByRole('button', { name: '发送问题' })).toBeDisabled()
  await page.getByLabel('你的问题').press('Control+Enter')
  await page.getByRole('button', { name: '刷新回答记录', exact: true }).click()
  await expect(page.getByRole('button', { name: '发送问题' })).toBeDisabled()
  expect(state.posts).toBe(1)
  state.failRestore = true
  await page.getByRole('button', { name: '刷新回答记录', exact: true }).click()
  await expect(trial.getByRole('alert')).toHaveText('管理试问当前不可用，请检查试问状态与索引就绪状态。')
  await expect(page.getByRole('button', { name: '发送问题' })).toBeDisabled()
  expect(state.posts).toBe(1)
  state.failRestore = false; state.pending = false; state.answer = true
  await page.getByRole('button', { name: '刷新回答记录', exact: true }).click()
  await expect(page.locator('.am-answer')).toHaveText('已恢复的回答。')
  await expect(trial.getByRole('alert')).toHaveCount(0)
  await expect(page.getByRole('button', { name: '发送问题' })).toBeEnabled()
  state.failClear = true
  await page.getByRole('button', { name: '清空试问' }).click()
  await expect(trial.getByRole('alert')).toHaveText('清空未确认完成，请重试。')
  await expect(page.locator('.am-answer')).toHaveText('已恢复的回答。')
  await expect(page.getByRole('button', { name: '发送问题' })).toBeDisabled()
  state.failClear = false
  await page.getByRole('button', { name: '清空试问' }).click()
  await expect(page.locator('.am-turn')).toHaveCount(0)
  await expect(trial.getByRole('status')).toContainText('已清空试问')
  expect(state.posts).toBe(1)

  const queries: string[] = []
  await page.route('**/api/v1/admin/assistant/sync?*', route => {
    const url = new URL(route.request().url()); queries.push(url.search)
    const offset = Number(url.searchParams.get('offset'))
    const items = Array.from({ length: offset ? 1 : 10 }, (_, index): SyncTask => ({ id: offset + index + 1, title: 'LongTitle'.repeat(25), source_type: 'article', source_id: offset + index + 1, target_version: '1', pipeline_version: 'studio-states-fixture-v1', operation: 'upsert', version: 1, attempt_count: 1, safe_error_code: 'provider_result_unknown', parent_task_id: null, operator_authorized: false, public_path: null, current_revision: true, resolved_by_current_index: false, created_at: '2026-09-10T00:00:00Z', updated_at: '2026-09-10T00:00:00Z', status: 'failed', provider_state: 'unknown', message: '结果待确认，请查看诊断。' }))
    return route.fulfill({ json: { items, total: 11, limit: 10, offset } })
  })
  await page.getByRole('navigation', { name: '助手管理视图' }).getByRole('link', { name: '概览' }).click()
  await page.getByRole('button', { name: '刷新状态' }).click()
  const dialog = page.getByRole('dialog')
  for (const theme of ['light', 'dark']) {
    await page.setViewportSize({ width: 1440, height: 900 })
    if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== (theme === 'dark')) await page.getByRole('button', { name: '切换颜色主题' }).click()
    await page.getByRole('button', { name: /查看内容/ }).click()
    await expect(dialog.locator('.am-task')).toHaveCount(10)
    for (const width of [320, 390, 768, 1440]) {
      await page.setViewportSize({ width, height: 600 })
      await expect.poll(() => dialog.evaluate(el => el.scrollWidth - el.clientWidth)).toBeLessThanOrEqual(1)
      expect((await new AxeBuilder({ page }).include('.admin-modal').withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
      await page.screenshot({ path: info.outputPath(`${theme[0]}${width}.png`), fullPage: true })
    }
    await dialog.getByRole('button', { name: '下一页' }).click()
    await expect(dialog.locator('.am-task')).toHaveCount(1)
    expect(queries.some(query => query.includes('offset=10'))).toBe(true)
    await expect(dialog.getByLabel('状态', { exact: true })).toBeVisible()
    await dialog.getByLabel('状态', { exact: true }).focus()
    await dialog.getByLabel('状态', { exact: true }).selectOption('failed')
    await expect(dialog.locator('.am-task')).toHaveCount(10)
    expect(queries.some(query => query.includes('offset=0') && query.includes('status=failed'))).toBe(true)
    await dialog.getByLabel('状态', { exact: true }).selectOption('')
    await page.keyboard.press('Escape')
    await expect(dialog).toHaveCount(0)
  }
})
