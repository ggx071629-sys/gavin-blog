import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

const api = 'http://127.0.0.1:8101/api/v1/assistant/_test/chat'

test('enabled assistant preserves active work, fences DELETE, and owns the responsive overlay', async ({ page, request }) => {
  await page.setViewportSize({ width: 1280, height: 800 })
  const sessionPosts: string[] = []
  const questionPosts: string[] = []
  page.on('request', (item) => {
    if (item.url().includes('/api/v1/assistant/sessions') && item.method() === 'POST') {
      sessionPosts.push(item.url())
    }
    if (item.url().includes('/api/v1/assistant/questions') && item.method() === 'POST') {
      questionPosts.push(item.url())
    }
  })

  await page.goto('/notes/2026/08/python-notes', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await page.getByTestId('assistant-launcher').click()
  await expect(page.getByTestId('assistant-panel')).toBeVisible()

  expect((await request.post(`${api}/hold`)).ok()).toBe(true)
  await page.getByLabel('问题').fill('Which published notes cover FastAPI?')
  await page.getByRole('button', { name: '发送' }).click()
  await expect.poll(async () => (await request.get(`${api}/started`)).json()).toEqual({ started: true })
  await expect(page.getByRole('button', { name: '发送' })).toBeDisabled()

  await page.reload({ waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await page.getByTestId('assistant-launcher').click()
  await expect(page.getByText('正在完成上一个问题')).toBeVisible()
  await expect(page.getByRole('button', { name: '发送' })).toBeDisabled()
  expect((await request.post(`${api}/release`)).ok()).toBe(true)
  await expect(page.getByTestId('assistant-answer')).toBeVisible({ timeout: 30_000 })
  expect(questionPosts).toHaveLength(1)

  await page.getByLabel('问题').fill('What did that previous answer say about FastAPI?')
  await page.getByRole('button', { name: '发送' }).click()
  await expect(page.getByTestId('assistant-answer')).toHaveCount(2, { timeout: 30_000 })
  expect(questionPosts).toHaveLength(2)

  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await page.getByTestId('assistant-launcher').click()
  const source = page.locator('.assistant-source-link').last()
  await source.click()
  await expect(page).toHaveURL(/\/notes\/\d{4}\/\d{2}\/python-notes$/)
  await expect.poll(() => page.evaluate(() => {
    const active = document.activeElement
    return active?.id === 'main-content' || active?.tagName === 'MAIN' || active?.tagName === 'H1'
  })).toBe(true)

  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  let captured!: () => void
  let release!: () => void
  const capturedGet = new Promise<void>((resolve) => { captured = resolve })
  const releaseGet = new Promise<void>((resolve) => { release = resolve })
  await page.route('**/api/v1/assistant/session', async (route) => {
    const response = await route.fetch()
    captured()
    await releaseGet
    await route.fulfill({ response })
  }, { times: 1 })
  await page.getByTestId('assistant-launcher').click()
  await capturedGet
  await page.getByRole('button', { name: '清除对话' }).click()
  const deleteResponse = page.waitForResponse(response =>
    response.url().endsWith('/api/v1/assistant/session') && response.request().method() === 'DELETE')
  await page.getByRole('button', { name: '确认清除' }).click()
  expect([202, 204]).toContain((await deleteResponse).status())
  release()
  await expect(page.getByTestId('assistant-question')).toHaveCount(0)
  await expect(page.getByTestId('assistant-answer')).toHaveCount(0)
  await page.getByRole('button', { name: '关闭问答面板' }).click()

  await page.setViewportSize({ width: 390, height: 844 })
  await page.getByRole('button', { name: '打开主导航菜单' }).click()
  await expect(page.locator('[aria-modal="true"]')).toHaveCount(1)
  await page.getByTestId('assistant-launcher').evaluate((element: HTMLElement) => element.click())
  await expect(page.getByTestId('assistant-modal')).toBeVisible()
  await expect(page.locator('[aria-modal="true"]')).toHaveCount(1)
  await page.keyboard.press('Tab')
  await page.keyboard.press('Escape')
  await expect(page.getByTestId('assistant-modal')).toBeHidden()

  for (const width of [390, 639, 640, 1024]) {
    await page.setViewportSize({ width, height: 844 })
    await page.getByTestId('assistant-launcher').click()
    await expect(page.getByTestId('assistant-modal')).toBeVisible()
    await expect(page.locator('[aria-modal="true"]')).toHaveCount(1)
    await page.getByRole('button', { name: '关闭问答面板' }).click()
  }
  await page.setViewportSize({ width: 1280, height: 800 })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.getByTestId('assistant-launcher').click()
  await expect(page.getByTestId('assistant-panel')).toBeVisible()
  await expect(page.locator('[aria-modal="true"]')).toHaveCount(0)

  const accessibility = await new AxeBuilder({ page }).include('#ask-gavin-panel').analyze()
  expect(accessibility.violations.filter(item => ['serious', 'critical'].includes(item.impact || ''))).toEqual([])
  expect(sessionPosts.length).toBeGreaterThanOrEqual(1)
})

test('admin kill switch is explicit and prevents a later anonymous admission', async ({ page }) => {
  await page.goto('/admin/login', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)

  await page.goto('/admin/assistant', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await expect(page.getByRole('heading', { name: '已向访客开放' })).toBeVisible()
  await page.getByRole('link', { name: '高级维护' }).click()
  await page.getByRole('button', { name: '紧急停止全部问答', exact: true }).click()
  const disabled = page.waitForResponse(response =>
    response.url().endsWith('/api/v1/admin/assistant/emergency-stop')
    && response.request().method() === 'POST')
  await page.getByRole('dialog').getByRole('button', { name: '紧急停止全部问答' }).click()
  expect((await disabled).status()).toBe(200)
  await expect(page.getByRole('button', { name: '恢复后台试问' })).toBeVisible()

  for (const width of [390, 640, 1024, 1280]) {
    await page.setViewportSize({ width, height: 844 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  }
  const accessibility = await new AxeBuilder({ page }).include('#admin-main').analyze()
  expect(accessibility.violations.filter(item => ['serious', 'critical'].includes(item.impact || ''))).toEqual([])

  const questionRequests: string[] = []
  page.on('request', (request) => {
    if (request.url().includes('/api/v1/assistant/questions')) questionRequests.push(request.url())
  })
  await page.goto('/notes/2026/08/python-notes', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await expect(page.getByTestId('assistant-launcher')).toHaveCount(0)
  await expect(page.getByTestId('assistant-orb')).toHaveCount(0)
  const availability = await page.request.get('/api/v1/assistant/availability')
  expect(await availability.json()).toEqual({ available: false })
  const admission = await page.request.post('/api/v1/assistant/sessions', { headers: { Origin: 'http://127.0.0.1:3101' } })
  expect(admission.status()).toBe(503)
  expect(questionRequests).toEqual([])
  // Restore the shared test service for later independent scenarios.
  await page.goto('/admin/assistant')
  await expectHydrated(page)
  await page.getByRole('button', { name: '向访客开放', exact: true }).click()
  await page.getByRole('dialog').getByRole('button', { name: '向访客开放' }).click()
  await expect(page.getByRole('heading', { name: '已向访客开放' })).toBeVisible()
})
