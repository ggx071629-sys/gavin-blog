import { expect, test } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

test('renew switched index from maintenance and explicitly resume trial', async ({ page }) => {
  await page.goto('/admin/login')
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  await page.goto('/admin/assistant?view=maintenance')
  await expectHydrated(page)
  const dialog = page.getByRole('dialog')
  await dialog.getByRole('button', { name: '重建公开知识索引', exact: true }).click()
  await dialog.getByRole('button', { name: '重建公开知识索引', exact: true }).click()
  const switchIndex = dialog.getByRole('button', { name: '切换到新索引', exact: true })
  await expect(switchIndex).toBeVisible({ timeout: 45000 })
  await switchIndex.click()
  await dialog.getByRole('button', { name: '切换到新索引', exact: true }).click()
  const renew = dialog.getByRole('button', { name: '校验并签发资格', exact: true })
  const resume = dialog.getByRole('button', { name: '恢复后台试问', exact: true })
  await expect(renew).toBeEnabled()
  await expect(resume).toBeDisabled()
  // A safe server failure remains visible in the dialog and permits retry.
  await page.route('**/api/v1/admin/assistant/readiness/renew', route => route.fulfill({
    status: 409, contentType: 'application/json',
    body: JSON.stringify({ error: { code: 'readiness_index_invalid', message: '索引完整性校验未通过，请检查内容同步。' } }),
  }), { times: 1 })
  await renew.click()
  await expect(dialog.getByRole('alert')).toContainText('索引完整性校验未通过')
  await expect(resume).toBeDisabled()
  const response = page.waitForResponse(r => r.url().endsWith('/readiness/renew') && r.status() === 200)
  await renew.click()
  const result = await (await response).json()
  expect(result.qualified).toBe(true)
  expect(result.generation_id).toBeGreaterThan(0)
  await expect(dialog.getByRole('status')).toContainText('运行资格已通过校验')
  await expect(resume).toBeEnabled()
  await resume.click()
  await expect(resume).toBeHidden()
  await expect(dialog.getByRole('link', { name: '前往试问' })).toBeVisible()
  await page.getByRole('button', { name: '关闭弹窗' }).click()
  await expect(page.getByRole('heading', { name: '已关闭对外问答' })).toBeVisible()
})
