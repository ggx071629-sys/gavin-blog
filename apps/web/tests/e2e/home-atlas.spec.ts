import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { join } from 'node:path'
import { expectHydrated } from '../support/hydration'

const sampleArticle = (id: number) => ({ id, title: `隔离样例 ${id}：从工程实践到可维护的系统边界`, summary: '', content: 'FULL_BODY_SENTINEL', published_at: '2026-09-06T00:00:00Z', public_path: `/notes/2026/09/sample-${id}` })
const sampleTaxonomy = (ids: number[], total = 200) => ({ categories: ids.map(id => ({ id, name: `工程栏目 ${id}`, slug: `sample-${id}`, article_count: 20 })), tags: [], total_article_count: total })
const enterHome = async (page: Page) => {
  await page.getByRole('link', { name: 'Gavin 首页', exact: true }).click()
  await expect(page.getByTestId('home-atlas')).toHaveAttribute('aria-busy', 'false')
}
const prepare = async (page: Page) => {
  await page.goto('/about', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
}

test('homepage atlas supports stable selection, hover, keyboard reset and real destinations', async ({ page }) => {
  await prepare(page)
  const requests: string[] = []
  await page.route('**/api/v1/taxonomy', route => { requests.push(route.request().url()); return route.fulfill({ json: sampleTaxonomy([8, 3, 6, 1, 4]) }) })
  await page.route('**/api/v1/articles?*', route => { requests.push(route.request().url()); return route.fulfill({ json: [sampleArticle(Number(new URL(route.request().url()).searchParams.get('category')?.split('-')[1] || 9))] }) })
  await enterHome(page)
  const nodes = page.getByTestId('atlas-node')
  await expect(nodes).toHaveText(['工程栏目 120 篇笔记', '工程栏目 320 篇笔记', '工程栏目 420 篇笔记'])
  await expect(page.getByTestId('atlas-article')).toHaveCount(3)
  await expect(page.getByTestId('atlas-all-categories')).toHaveAttribute('href', '/articles')
  await expect(page.getByTestId('atlas-all-categories')).toHaveText('更多领域')
  await nodes.nth(0).focus()
  await expect(page.getByTestId('atlas-branch').nth(0)).toHaveAttribute('data-active', 'true')
  await page.keyboard.press('Enter')
  await expect(nodes.nth(0)).toHaveAttribute('aria-pressed', 'true')
  await nodes.nth(1).hover()
  await expect(page.getByTestId('atlas-branch').nth(1)).toHaveAttribute('data-active', 'true')
  await page.getByRole('heading', { level: 1 }).hover()
  await expect(page.getByTestId('atlas-branch').nth(0)).toHaveAttribute('data-active', 'true')
  await expect(page.getByTestId('atlas-selection')).toHaveText('沿着「工程栏目 1」继续探索')
  await nodes.nth(1).focus()
  await page.keyboard.press('Space')
  await expect(nodes.nth(0)).toHaveAttribute('aria-pressed', 'false')
  await expect(nodes.nth(1)).toHaveAttribute('aria-pressed', 'true')
  await page.getByRole('button', { name: '查看全部路线' }).focus()
  await page.keyboard.press('Enter')
  await expect(page.locator('[data-testid="atlas-node"][aria-pressed="true"]')).toHaveCount(0)
  await expect(page.locator('[data-testid="atlas-branch"][data-active="true"]')).toHaveCount(0)
  await expect(page.getByRole('link', { name: '浏览工程栏目 1栏目' })).toHaveAttribute('href', '/articles?category=sample-1')
  await expect(page.getByTestId('atlas-article').first()).toHaveAttribute('href', '/notes/2026/09/sample-1')
  expect(requests).toHaveLength(5)
  await page.waitForTimeout(500)
  expect(requests).toHaveLength(5)
})

test('homepage distinguishes loading, empty, uncategorized and partial failures with retry', async ({ page }) => {
  await prepare(page)
  let mode = 'loading'
  let release!: () => void
  const held = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/v1/taxonomy', async (route) => {
    if (mode === 'loading') await held
    if (mode === 'taxonomy-error') return route.fulfill({ status: 503, json: { detail: 'unavailable' } })
    return route.fulfill({ json: mode === 'partial' || mode === 'recovered' ? sampleTaxonomy([1, 2]) : sampleTaxonomy([], mode === 'empty' ? 0 : 9) })
  })
  await page.route('**/api/v1/articles?*', (route) => {
    const category = new URL(route.request().url()).searchParams.get('category')
    if (mode === 'partial' && category === 'sample-1') return route.fulfill({ status: 503, json: { detail: 'unavailable' } })
    return route.fulfill({ json: mode === 'loading' || mode === 'empty' || (mode === 'partial' && category === 'sample-2') ? [] : [sampleArticle(9)] })
  })
  await page.getByRole('link', { name: 'Gavin 首页', exact: true }).click()
  await expect(page.getByTestId('home-loading')).toBeVisible()
  await expect(page.getByTestId('home-empty')).toHaveCount(0)
  mode = 'empty'; release()
  await expect(page.getByTestId('home-empty')).toBeVisible()
  await expect(page.getByTestId('atlas-node')).toHaveCount(0)
  await expect(page.getByTestId('atlas-unavailable')).toHaveCount(0)
  // A new route visit re-reads the source; no background polling is required.
  for (const state of ['uncategorized', 'taxonomy-error', 'partial']) {
    await prepare(page)
    mode = state
    await enterHome(page)
    await expect(page.getByTestId('home-empty')).toHaveCount(0)
    if (state === 'uncategorized') {
      await expect(page.getByTestId('atlas-fallback')).toContainText('从最近一篇开始')
      await expect(page.getByTestId('atlas-node')).toHaveCount(0)
      await expect(page.getByTestId('atlas-fallback').getByRole('link')).toHaveAttribute('href', '/notes/2026/09/sample-9')
    }
    if (state === 'taxonomy-error') {
      await expect(page.getByTestId('atlas-unavailable')).toBeVisible()
      await expect(page.getByTestId('home-atlas')).not.toContainText('0 篇')
    }
    if (state === 'partial') {
      await expect(page.getByTestId('atlas-error')).toBeVisible()
      await expect(page.getByTestId('atlas-empty')).toBeVisible()
      mode = 'recovered'
      await page.getByRole('button', { name: '重试读取' }).click()
      await expect(page.getByTestId('atlas-article')).toHaveCount(2)
      await expect(page.getByRole('button', { name: '重试读取' })).toHaveCount(0)
    }
  }
})

test('homepage atlas adapts long content to both themes and narrow short viewports', async ({ page }, testInfo) => {
  await prepare(page)
  const data = sampleTaxonomy([1, 2, 3, 4, 5, 6, 7, 8])
  data.categories[0]!.name = '工程实践与人工智能应用开发的长期记录'
  await page.route('**/api/v1/taxonomy', route => route.fulfill({ json: data }))
  await page.route('**/api/v1/articles?*', route => route.fulfill({ json: [1, 2, 3, 4].map(id => ({ ...sampleArticle(id), title: `隔离长标题 ${id} ${'LongUnbrokenEngineeringTitle'.repeat(3)}` })) }))
  await enterHome(page)
  await page.emulateMedia({ reducedMotion: 'reduce' })
  for (const theme of ['light', 'dark']) {
    if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== (theme === 'dark')) await page.getByRole('button', { name: '切换颜色主题' }).click()
    for (const width of [320, 390, 639, 640, 768, 1023, 1024, 1280, 1440]) {
      await page.setViewportSize({ width, height: 480 })
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), { message: `${theme}/${width}` }).toBe(true)
      await expect(page.getByTestId('atlas-node')).toHaveCount(3)
      await expect(page.getByTestId('home-note-row')).toHaveCount(3)
      expect(await page.getByTestId('atlas-node').first().evaluate(el => el.getBoundingClientRect().height)).toBeGreaterThanOrEqual(44)
      expect(await page.locator('.knowledge-line-active').first().evaluate(el => Math.max(...getComputedStyle(el).transitionDuration.split(',').map(value => parseFloat(value))))).toBeLessThanOrEqual(0.00001)
      if ([320, 390, 1024, 1440].includes(width)) await page.screenshot({ path: join(testInfo.project.outputDir, `h-${theme}-${width}.png`), fullPage: true })
    }
    expect(await page.locator('html').evaluate(el => getComputedStyle(el).opacity)).toBe('1')
    expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
  }
  await expect(page.getByTestId('profile-card').getByText('Live', { exact: true })).toHaveCount(0)
  await expect(page.locator('.home-note-summary')).toHaveCount(0)
})

test('homepage reads published categories and latest snapshots with bounded requests', async ({ page }, testInfo) => {
  await page.goto('/admin/login', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  const csrf = (await page.context().cookies()).find(cookie => cookie.name === 'gavin_csrf')!.value
  const headers = { 'X-CSRF-Token': csrf }
  for (let index = 0; index < 4; index++) {
    const categoryResponse = await page.request.post('/api/v1/admin/categories', { headers, data: { name: `首页验收 ${index}`, slug: `home-live-${index}` } })
    expect(categoryResponse.status()).toBe(201)
    const category = await categoryResponse.json()
    const created = await page.request.post('/api/v1/admin/articles', { headers, data: { title: `首页隔离样例 ${index}`, slug: `home-live-${index}`, category_id: category.id, summary: '', content: 'HOME_FULL_BODY_SENTINEL\n\n' + '这是隔离测试的正文。'.repeat(100) } })
    expect(created.status()).toBe(201)
    const article = await created.json()
    expect((await page.request.post(`/api/v1/admin/articles/${article.id}/publish`, { headers, data: { version: article.version } })).ok()).toBe(true)
    // A saved working copy must never replace the public title.
    const current = await (await page.request.get(`/api/v1/admin/articles/${article.id}`)).json()
    expect((await page.request.patch(`/api/v1/admin/articles/${article.id}`, { headers, data: { title: `UNPUBLISHED_HOME_${index}`, version: current.version } })).ok()).toBe(true)
  }
  const taxonomy = await (await page.request.get('/api/v1/taxonomy')).json()
  const categories = [...taxonomy.categories].sort((a, b) => a.id - b.id).slice(0, 3)
  const expectedArticles = await Promise.all(categories.map(async category => (await (await page.request.get(`/api/v1/articles?category=${category.slug}&limit=1&offset=0`)).json())[0]))
  const response = await page.goto('/', { waitUntil: 'networkidle' })
  expect(response?.status()).toBe(200)
  const html = await response!.text()
  expect(html).not.toContain('HOME_FULL_BODY_SENTINEL')
  expect(html).not.toContain('UNPUBLISHED_HOME_')
  await expectHydrated(page)
  await expect(page.getByTestId('atlas-node')).toHaveCount(3)
  for (let index = 0; index < 3; index++) {
    await expect(page.getByTestId('atlas-node').nth(index)).toContainText(categories[index].name)
    await expect(page.getByTestId('atlas-article').nth(index)).toHaveAttribute('href', expectedArticles[index].public_path)
  }
  await page.getByTestId('atlas-article').first().click()
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(expectedArticles[0].title)
  const requests: string[] = []
  const payloads: Promise<{ path: string, bytes: number }>[] = []
  page.on('request', request => { if (/\/api\/v1\/(articles\?|taxonomy$)/.test(request.url())) requests.push(request.url()) })
  page.on('response', response => { if (/\/api\/v1\/(articles\?|taxonomy$)/.test(response.url())) payloads.push(response.body().then(body => ({ path: new URL(response.url()).pathname + new URL(response.url()).search, bytes: body.length }))) })
  await enterHome(page)
  expect(requests).toHaveLength(5)
  await testInfo.attach('homepage-api-payloads', { body: JSON.stringify(await Promise.all(payloads), null, 2), contentType: 'application/json' })
})
