import { expect, test, type Page } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

const policy = { question_max_chars: 500, session_idle_seconds: 1800, session_absolute_seconds: 14400, body_retention_seconds: 1800 }
async function mockAssistant(page: Page) {
  const state = { requests: 0 }
  await page.route('**/api/v1/assistant/**', route => {
    if (route.request().url().endsWith('/availability')) return route.fulfill({ json: { available: true } })
    state.requests++
    return route.fulfill({ json: route.request().url().endsWith('/sessions') ? { policy } : {
      session_id: 'discovery', created_at: '2026-09-09', idle_expires_at: '2026-09-10', absolute_expires_at: '2026-09-10', policy, turns: [], active_turn: null,
    } })
  })
  return state
}

test('assistant discovery stays in navigation and remembers dismissal without eager requests', async ({ page }) => {
  const state = await mockAssistant(page)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/about')
  await expectHydrated(page)
  const launcher = page.getByTestId('assistant-launcher'), orb = page.getByTestId('assistant-orb'), hint = page.getByTestId('assistant-orb-hint')
  await expect(launcher).toBeVisible()
  await expect(orb).toBeVisible()
  await expect(hint).toHaveCount(0)
  await expect(hint).toBeVisible({ timeout: 7000 })
  await expect(hint).toContainText('影响阅读？可以关闭这条提示。')
  const rect = await hint.boundingBox()
  expect(rect!.x).toBeGreaterThanOrEqual(0)
  expect(rect!.x + rect!.width).toBeLessThanOrEqual(390)
  expect(rect!.y + rect!.height).toBeLessThanOrEqual(844)
  expect(state.requests).toBe(0)
  await page.getByRole('button', { name: '关闭使用提示' }).click()
  await expect(hint).toHaveCount(0)
  await expect(orb).toBeFocused()
  await page.reload()
  await expectHydrated(page)
  await page.waitForTimeout(3200)
  await expect(hint).toHaveCount(0)
  expect(state.requests).toBe(0)
  await orb.click()
  await expect(page.getByLabel('问题', { exact: true })).toBeEnabled()
  await expect(page.locator('[aria-modal="true"]')).toHaveCount(1)
  await expect(orb).toBeHidden()
  await page.getByRole('button', { name: '关闭问答面板' }).click()
  await expect(orb).toBeFocused()
  await expect(page.locator('[inert]')).toHaveCount(0)
  await page.getByRole('button', { name: '打开主导航菜单' }).click()
  await expect(orb).toBeHidden()
  await page.getByTestId('site-menu-overlay').getByRole('button', { name: '关闭主导航菜单' }).click()
  await expect(orb).toBeVisible()
  await expect(page.locator('[inert]')).toHaveCount(0)
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/')
  await expectHydrated(page)
  await expect(page.getByTestId('assistant-discovery')).toHaveCount(0)
  await expect(page.getByRole('button', { name: '开始提问' })).toHaveCount(0)
  await launcher.click()
  await expect(page.getByRole('dialog', { name: '问 Gavin', exact: true })).toBeVisible()
  await page.getByRole('button', { name: '关闭问答面板' }).click()
  await expect(launcher).toBeFocused()
  await page.goto('/admin/login')
  await expectHydrated(page)
  await expect(launcher).toHaveCount(0)
  await expect(orb).toHaveCount(0)
  await expect(hint).toHaveCount(0)
})

test('assistant discovery tolerates blocked preference storage', async ({ page }) => {
  await page.addInitScript(() => {
    const getItem = Storage.prototype.getItem
    Storage.prototype.getItem = function (key) {
      if (key.startsWith('gavin:assistant-orb')) throw new Error('storage blocked')
      return getItem.call(this, key)
    }
    const setItem = Storage.prototype.setItem
    Storage.prototype.setItem = function (key, value) {
      if (key.startsWith('gavin:assistant-orb')) throw new Error('storage blocked')
      return setItem.call(this, key, value)
    }
  })
  await page.goto('/')
  await expectHydrated(page)
  await expect(page.getByTestId('assistant-orb-hint')).toBeVisible({ timeout: 7000 })
  await page.getByRole('button', { name: '关闭使用提示' }).click()
  await page.getByRole('link', { name: '关于', exact: true }).click()
  await page.getByRole('link', { name: 'Gavin 首页' }).click()
  await page.waitForTimeout(3200)
  await expect(page.getByTestId('assistant-orb-hint')).toHaveCount(0)
  await expect(page.getByTestId('assistant-orb')).toBeVisible()
  await expect(page.getByTestId('assistant-launcher')).toBeVisible()
})

test('assistant orb drags with mouse and touch without opening and restores bounded position', async ({ page, context }) => {
  const state = await mockAssistant(page)
  await page.goto('/')
  await expectHydrated(page)
  const orb = page.getByTestId('assistant-orb'), hint = page.getByTestId('assistant-orb-hint')
  // Opening through the retained header before the timer fires also ends guidance.
  await page.getByTestId('assistant-launcher').click()
  await expect(page.getByLabel('问题', { exact: true })).toBeEnabled()
  await page.getByRole('button', { name: '关闭问答面板' }).click()
  await page.waitForTimeout(3200)
  await expect(hint).toHaveCount(0)
  const before = state.requests
  const start = (await orb.boundingBox())!
  await page.mouse.move(start.x + 26, start.y + 26)
  await page.mouse.down()
  await page.mouse.move(45, 320, { steps: 10 })
  await page.mouse.up()
  await expect(page.getByRole('dialog', { name: '问 Gavin', exact: true })).toBeHidden()
  expect(state.requests).toBe(before)
  expect((await orb.boundingBox())!.x).toBeCloseTo(16, 0)
  const savedY = (await orb.boundingBox())!.y
  await page.reload()
  await expectHydrated(page)
  await expect(orb).toBeVisible()
  expect((await orb.boundingBox())!.x).toBeCloseTo(16, 0)
  expect((await orb.boundingBox())!.y).toBeCloseTo(savedY, 0)
  await expect(hint).toHaveCount(0)
  for (const width of [320, 390, 639, 768, 1280]) {
    await page.setViewportSize({ width, height: 600 })
    await expect.poll(async () => { const r = (await orb.boundingBox())!; return r.x >= 0 && r.y >= 0 && r.x + r.width <= width && r.y + r.height <= 600 }).toBe(true)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  }
  await page.setViewportSize({ width: 390, height: 700 })
  const cdp = await context.newCDPSession(page)
  const touchStart = (await orb.boundingBox())!
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: touchStart.x + 26, y: touchStart.y + 26 }] })
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: 340, y: 400 }] })
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] })
  await expect(page.getByRole('dialog', { name: '问 Gavin', exact: true })).toHaveCount(0)
  const end = (await orb.boundingBox())!
  expect(end.x).toBeGreaterThan(300)
  expect(end.x + end.width).toBeLessThanOrEqual(390)
  await orb.focus()
  await orb.press('ArrowLeft')
  expect((await orb.boundingBox())!.x).toBeCloseTo(16, 0)
  await orb.press('Enter')
  await expect(page.getByRole('dialog', { name: '问 Gavin', exact: true })).toBeVisible()
  await cdp.detach()
})
