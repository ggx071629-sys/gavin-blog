import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

test('dialogs', async ({ page }, info) => {
  test.setTimeout(180000)
  await page.goto('/admin/login')
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  await page.route('**/api/v1/admin/assistant/management', async route => {
    const response = await route.fetch()
    const value = await response.json()
    value.budget = { ...value.budget, cap_micro_cny: 1000000, ceiling_micro_cny: 2000000, version: 23 }
    await route.fulfill({ response, json: value })
  })
  await page.goto('/admin/assistant')
  await expectHydrated(page)
  await expect(page.locator('.am-availability')).toBeVisible()
  const dialog = page.getByRole('dialog')
  for (const theme of ['light', 'dark']) {
    await page.setViewportSize({ width: 1440, height: 900 })
    if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== (theme === 'dark')) await page.getByRole('button', { name: '切换颜色主题' }).click()
    for (const [index, name] of ['费用明细', '查看内容', '修改预算', '高级维护'].entries()) {
      const opener = name === '高级维护' ? page.getByRole('link', { name }) : page.getByRole('button', { name: name === '修改预算' ? name : new RegExp(name) })
      await opener.click()
      await expect(dialog).toHaveCount(1)
      await expect(dialog).toBeVisible()
      for (const width of [320, 390, 1440]) {
        await page.setViewportSize({ width, height: width === 320 ? 480 : 900 })
        await expect.poll(() => dialog.evaluate(el => el.scrollWidth - el.clientWidth)).toBeLessThanOrEqual(1)
        expect((await new AxeBuilder({ page }).include('.admin-modal').withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
        await page.screenshot({ path: info.outputPath(`${index}${theme[0]}${width}.png`), fullPage: true })
      }
      await dialog.getByRole('button', { name: '关闭弹窗' }).focus()
      await page.keyboard.press('Shift+Tab')
      expect(await dialog.evaluate(el => el.contains(document.activeElement))).toBe(true)
      await page.keyboard.press('Escape')
      await expect(dialog).toHaveCount(0)
      await expect(opener).toBeFocused()
      expect(await page.evaluate(() => document.body.style.overflow)).toBe('')
    }
  }
  const syncTask = { id: 901, source_type: 'article', source_id: 9, target_version: 'v1', pipeline_version: 'v1', operation: 'upsert', status: 'failed', version: 7, attempt_count: 1, safe_error_code: 'worker_unavailable', message: '等待安全重试', parent_task_id: null, operator_authorized: false, created_at: '2026-09-10T00:00:00Z', updated_at: '2026-09-10T00:00:00Z', title: '可重试公开文章', public_path: null, current_revision: true, provider_state: 'failed' }
  await page.route('**/api/v1/admin/assistant/sync?*', route => route.fulfill({ json: { items: [syncTask, { ...syncTask, id: 902, title: '结果未知的文章', provider_state: 'unknown' }], total: 2, limit: 10, offset: 0 } }))
  await page.getByRole('button', { name: '刷新状态' }).click()
  await page.getByRole('button', { name: /查看内容/ }).click()
  await expect(dialog.getByRole('button', { name: '重试此内容同步' })).toHaveCount(1)
  await expect(dialog.locator('.am-task').filter({ hasText: '结果未知的文章' }).getByRole('link', { name: '查看诊断' })).toBeVisible()
  let retryBody: unknown
  await page.route('**/api/v1/admin/assistant/index/tasks/901/retry', route => {
    retryBody = route.request().postDataJSON()
    return route.fulfill({ status: 409, json: { detail: '同步任务版本已变化' } })
  })
  await dialog.getByRole('button', { name: '重试此内容同步' }).click()
  await expect(dialog.getByRole('alert')).toContainText('同步任务版本已变化')
  expect(retryBody).toEqual({ expected_status: 'failed', expected_version: 7, operator_authorized: false })
  await dialog.getByRole('button', { name: '关闭弹窗' }).click()
  await page.getByRole('button', { name: '刷新状态' }).click()
  await page.getByRole('button', { name: '修改预算', exact: true }).click()
  await page.getByLabel('每日总预算（元）').fill('1e3')
  await dialog.getByRole('button', { name: '保存预算' }).click()
  await expect(dialog.getByRole('alert')).toContainText('请输入非负金额')
  let submittedBudget: unknown
  await page.route('**/api/v1/admin/assistant/budget', async route => {
    submittedBudget = route.request().postDataJSON()
    await route.fulfill({ status: 409, json: { detail: '版本已变化' } })
  })
  await page.getByLabel('每日总预算（元）').fill('1.000001')
  await dialog.getByRole('button', { name: '保存预算' }).click()
  await expect(dialog.getByText('保存未完成。输入已保留', { exact: false })).toBeVisible()
  await expect(page.getByLabel('每日总预算（元）')).toHaveValue('1.000001')
  expect(submittedBudget).toEqual({ cap_micro_cny: 1000001, expected_version: 23 })
  await dialog.getByRole('button', { name: '取消', exact: true }).click()
  await page.goto('/admin/assistant?view=maintenance')
  await expectHydrated(page)
  await expect(dialog.getByRole('heading', { name: '高级维护', exact: true })).toBeVisible()
  await expect(dialog.getByRole('button', { name: '关闭弹窗' })).toBeFocused()
  let emergencyRequests = 0
  await page.route('**/api/v1/admin/assistant/emergency-stop', route => {
    emergencyRequests++
    return route.fulfill({ status: 503, json: { detail: '隔离停止失败' } })
  })
  await dialog.getByRole('button', { name: '紧急停止全部问答', exact: true }).click()
  await expect(dialog).toHaveCount(1)
  await dialog.getByRole('button', { name: '取消', exact: true }).click()
  expect(emergencyRequests).toBe(0)
  await expect(dialog.getByRole('heading', { name: '高级维护', exact: true })).toBeVisible()
  await dialog.getByRole('button', { name: '紧急停止全部问答', exact: true }).click()
  await dialog.getByRole('button', { name: '紧急停止全部问答', exact: true }).click()
  await expect(dialog.getByRole('alert')).toContainText('隔离停止失败')
  await expect(dialog.getByRole('button', { name: '紧急停止全部问答', exact: true })).toBeEnabled()
  expect(emergencyRequests).toBe(1)
  await page.keyboard.press('Escape')
  await expect(dialog.getByRole('heading', { name: '高级维护', exact: true })).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(dialog).toHaveCount(0)
  await expect(page).toHaveURL(/\/admin\/assistant$/)
})
