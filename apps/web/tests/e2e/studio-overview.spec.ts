import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { expectHydrated } from '../support/hydration'
import { money } from '../../utils/assistant-management'

test('overview', async ({ page }, info) => {
  test.setTimeout(180000)
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto('/admin/login')
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  const response = await page.request.get('/api/v1/admin/assistant/management')
  expect(response.ok()).toBe(true)
  const real = await response.json()
  const writes: string[] = []
  page.on('request', request => {
    if (request.url().includes('/admin/assistant') && request.method() !== 'GET') writes.push(request.url())
  })
  await page.goto('/admin/assistant')
  await expectHydrated(page)
  await expect(page.locator('.am-amount')).toContainText(money(real.usage_known ? real.budget.settled_micro_cny : null))
  await expect(page.locator('.am-amount')).toContainText(money(real.budget.cap_micro_cny))
  // A controlled failed queue uses the real snapshot shape, without mutating service state.
  await page.route('**/api/v1/admin/assistant', async route => {
    const response = await route.fetch()
    const value = await response.json()
    value.queue.failed = 2
    await route.fulfill({ response, json: value })
  })
  await page.getByRole('button', { name: '刷新状态' }).click()
  await expect(page.getByRole('heading', { name: '2 项内容同步失败' })).toBeVisible()
  await expect(page.locator('.am-issue').first().locator('.studio-icon')).toHaveAttribute('aria-hidden', 'true')
  for (const theme of ['light', 'dark']) {
    await page.setViewportSize({ width: 1487, height: 1058 })
    if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== (theme === 'dark')) await page.getByRole('button', { name: '切换颜色主题' }).click()
    for (const width of [320, 390, 768, 1024, 1487]) {
      await page.setViewportSize({ width, height: 1058 })
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1)
      if (width === 1487) {
        expect(await page.locator('.am-header h1').evaluate(el => getComputedStyle(el).fontSize)).toBe('38px')
        const row = await page.locator('.am-row').first().evaluate(el => getComputedStyle(el).gridTemplateColumns)
        expect(row).toMatch(/^318px /)
      }
      if ([320, 1487].includes(width)) {
        expect((await new AxeBuilder({ page }).include('.assistant-management').withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
        await page.screenshot({ path: info.outputPath(`${theme[0]}${width}.png`), fullPage: true, animations: 'disabled' })
      }
    }
  }
  await page.route('**/api/v1/admin/assistant/management', async route => {
    const response = await route.fetch()
    await route.fulfill({ response, json: { ...await response.json(), usage_known: false } })
  })
  await page.getByRole('button', { name: '刷新状态' }).click()
  await expect(page.locator('.am-amount')).toContainText('暂不可确认')
  await expect(page.getByRole('progressbar', { name: '今日预算占用' })).toHaveCount(0)
  await expect(page.getByText('预算占用暂不可确认')).toBeVisible()
  await page.unroute('**/api/v1/admin/assistant')
  await page.route('**/api/v1/admin/assistant', route => route.fulfill({ status: 503, json: { detail: '隔离读取失败' } }))
  await page.getByRole('button', { name: '刷新状态' }).click()
  await expect(page.getByText(/以下事实可能已过期/)).toBeVisible()
  await expect(page.getByRole('heading', { name: '当前状态待确认' })).toBeVisible()
  await expect(page.locator('.am-dot')).toHaveAttribute('data-open', 'false')
  expect(writes).toEqual([])
  expect(errors).toEqual([])
})
