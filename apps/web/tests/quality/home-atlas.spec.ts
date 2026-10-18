import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

let captureSequence = 0

// production homepage records real payloads, first paint and dual theme composition
test('q3', async ({ page }, testInfo) => {
  const diagnostics: string[] = []
  page.on('pageerror', error => diagnostics.push(error.message))
  page.on('console', message => { if (['warning', 'error'].includes(message.type())) diagnostics.push(message.text()) })
  await page.goto('/admin/login', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  const csrf = (await page.context().cookies()).find(cookie => cookie.name === 'gavin_csrf')!.value
  const headers = { 'X-CSRF-Token': csrf }
  const currentProfile = await (await page.request.get('/api/v1/admin/profile')).json()
  expect((await page.request.patch('/api/v1/admin/profile', {
    headers, data: { ...currentProfile, github_url: 'https://github.com/gavinhub', website_url: 'https://example.com', email: 'test@example.com', email_visible: true, resume_url: 'https://example.com/resume.pdf' },
  })).ok()).toBe(true)
  for (const [index, name] of ['Agent 开发', '云服务器', 'Web 工程'].entries()) {
    const categoryResponse = await page.request.post('/api/v1/admin/categories', { headers, data: { name, slug: `phase-two-quality-${index}` } })
    expect(categoryResponse.status()).toBe(201)
    const category = await categoryResponse.json()
    const title = ['让 Agent 的工具调用可以恢复', '从配置到续期：记录 HTTPS 部署', '一个页面，从请求到渲染'][index]
    const response = await page.request.post('/api/v1/admin/articles', { headers, data: { title, slug: `phase-two-quality-${index}`, category_id: category.id, summary: index === 2 ? '记录一次完整的页面加载过程，沿着真实请求理解渲染与交互的边界。' : '', content: 'PRODUCTION_BODY_SENTINEL\n\n' + '用于第二阶段生产构建验证的隔离样例。'.repeat(300) } })
    expect(response.status()).toBe(201)
    const article = await response.json()
    expect((await page.request.post(`/api/v1/admin/articles/${article.id}/publish`, { headers, data: { version: article.version } })).ok()).toBe(true)
  }
  const metrics: unknown[] = []
  for (const theme of ['light', 'dark']) {
    await page.evaluate(value => localStorage.setItem('nuxt-color-mode', value), theme)
    for (const width of [390, 1440]) {
      await page.setViewportSize({ width, height: 900 })
      const response = await page.goto('/', { waitUntil: 'networkidle' })
      await expectHydrated(page)
      const html = await response!.text()
      expect(html).not.toContain('PRODUCTION_BODY_SENTINEL')
      await expect(page.getByTestId('atlas-article')).toHaveCount(3)
      await expect(page.getByTestId('profile-github')).toBeVisible()
      await expect(page.getByTestId('profile-email')).toBeVisible()
      if (width === 1440) {
        const github = await page.getByTestId('profile-github').boundingBox()
        const email = await page.getByTestId('profile-email').boundingBox()
        expect(email!.y).toBe(github!.y)
      }
      await page.evaluate(() => document.fonts.ready)
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true)
      expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
      const measured = await page.evaluate(() => {
        const nav = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming
        return {
          ttfbMs: Math.round(nav.responseStart - nav.startTime),
          domContentLoadedMs: Math.round(nav.domContentLoadedEventEnd - nav.startTime),
          fcpMs: Math.round(performance.getEntriesByName('first-contentful-paint')[0]?.startTime ?? 0),
          htmlBytes: nav.decodedBodySize,
          hydrationApiRequests: performance.getEntriesByType('resource').filter(entry => entry.name.includes('/api/v1/')).map(entry => entry.name),
        }
      })
      expect(measured.hydrationApiRequests).toEqual([])
      metrics.push({ theme, width, ...measured })
      if (width === 1440) await expect(page.locator('.notebook-actions').getByRole('link', { name: /浏览文章/ })).toBeInViewport()
      await page.screenshot({ path: testInfo.outputPath(`${captureSequence++}.png`), fullPage: true })
    }
  }
  await page.goto('/about', { waitUntil: 'networkidle' })
  const payloads: Promise<{ path: string, bytes: number }>[] = []
  page.on('response', response => {
    if (/\/api\/v1\/(articles\?|taxonomy$)/.test(response.url())) payloads.push(response.body().then(body => ({ path: new URL(response.url()).pathname + new URL(response.url()).search, bytes: body.length })))
  })
  await page.getByRole('link', { name: 'Gavin 首页', exact: true }).click()
  await expect(page.getByTestId('home-atlas')).toHaveAttribute('aria-busy', 'false')
  const bodies = await Promise.all(payloads)
  expect(bodies).toHaveLength(5)
  console.log('Homepage measurements:', JSON.stringify({ metrics, payloads: bodies }))
  await testInfo.attach('homepage-measurements', { body: JSON.stringify({ metrics, payloads: bodies }, null, 2), contentType: 'application/json' })
  expect(diagnostics).toEqual([])
})
