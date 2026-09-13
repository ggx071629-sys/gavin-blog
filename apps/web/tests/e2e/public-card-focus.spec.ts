import { expect, test, type Locator, type Page } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

const opacity = (card: Locator) => card.evaluate(el => getComputedStyle(el, '::after').opacity)
const checkGlow = async (page: Page, card: Locator) => {
  await card.evaluate(el => el.scrollIntoView({ behavior: 'instant', block: 'center' }))
  await page.mouse.move(0, 0)
  let previousBox = ''
  await expect.poll(async () => {
    const currentBox = JSON.stringify(await card.boundingBox())
    const stable = currentBox !== 'null' && currentBox === previousBox
    previousBox = currentBox
    return stable
  }).toBe(true)
  const rect = (await card.boundingBox())!
  const border = await card.evaluate(el => el.clientLeft)
  const positions: string[] = []
  for (const fraction of [0.3, 0.7]) {
    await page.mouse.move(rect.x + rect.width * fraction, rect.y + rect.height / 2)
    await expect(card).toHaveAttribute('data-focus-glow', '')
    await expect.poll(() => card.evaluate((el, expected) => Math.abs(parseFloat((el as HTMLElement).style.getPropertyValue('--focus-pointer-x')) - expected), rect.width * fraction - border)).toBeLessThan(1)
    const style = await card.evaluate(el => {
      const s = getComputedStyle(el, '::after')
      return { image: s.backgroundImage, size: s.backgroundSize, position: s.backgroundPosition, events: s.pointerEvents, radius: s.borderRadius, cardRadius: getComputedStyle(el).borderRadius }
    })
    expect(style.image).toContain('radial-gradient')
    expect(style.size).toBe('160px 160px')
    expect(style.events).toBe('none')
    expect(style.radius).toBe(style.cardRadius)
    positions.push(style.position)
  }
  expect(positions[0]).not.toBe(positions[1])
  expect(await card.boundingBox()).toEqual(rect)
  await page.mouse.move(0, 0)
  await expect(card).not.toHaveAttribute('data-focus-glow', '')
  await expect.poll(() => card.evaluate(el => getComputedStyle(el, '::after').backgroundImage)).toBe('none')
}
const login = async (page: Page) => {
  await page.goto('/admin/login')
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  return { 'X-CSRF-Token': (await page.context().cookies()).find(c => c.name === 'gavin_csrf')!.value }
}

const seed = async (page: Page) => {
  const headers = await login(page)
  const suffix = Date.now().toString(36)
  const categoryResponse = await page.request.post('/api/v1/admin/categories', { headers, data: { name: `Focus ${suffix}`, slug: `focus-${suffix}` } })
  expect(categoryResponse.ok()).toBe(true)
  const category = await categoryResponse.json()
  const publish = async (type: string, data: Record<string, unknown>) => {
    const created = await page.request.post(`/api/v1/admin/${type}`, { headers, data: { content: `## 起点\n\n${'聚焦反馈保持阅读位置。'.repeat(180)}\n\n## 结论\n\n可继续查阅。`, ...data } })
    expect(created.ok(), await created.text()).toBe(true)
    const draft = await created.json()
    const published = await page.request.post(`/api/v1/admin/${type}/${draft.id}/publish`, { headers, data: { version: draft.version } })
    expect(published.ok(), await published.text()).toBe(true)
    return published.json()
  }
  const article = await publish('articles', { title: 'CardFocus 样例', slug: `focus-${suffix}`, category_id: category.id, summary: '用于隔离验证的公开卡片。' })
  await publish('articles', { title: 'CardFocus 关联', slug: `focus-related-${suffix}`, category_id: category.id })
  const project = await publish('projects', { title: 'CardFocus 工程', slug: `focus-${suffix}`, article_ids: [article.id] })
  await publish('projects', { title: 'CardFocus 另一个工程', slug: `focus-next-${suffix}` })
  const book = await publish('books', { book_title: 'CardFocus 书籍', slug: `focus-${suffix}`, author: '测试作者', reading_status: 'reading' })
  await publish('books', { book_title: 'CardFocus 已读书籍', slug: `focus-next-${suffix}`, author: '测试作者', reading_status: 'completed' })
  return { article, project, book }
}

const checkCard = async (page: Page, card: Locator) => {
  await page.evaluate(() => { document.documentElement.style.scrollBehavior = 'auto' })
  await card.evaluate(el => el.scrollIntoView({ behavior: 'instant', block: 'center' }))
  await page.mouse.move(0, 0)
  await expect.poll(() => opacity(card)).toBe('0')
  const before = await card.boundingBox()
  await page.mouse.move(before!.x + before!.width / 2, before!.y + before!.height / 2)
  await expect.poll(() => card.evaluate(el => ({ opacity: getComputedStyle(el, '::after').opacity, hovered: el.matches(':hover'), scoped: document.documentElement.dataset.publicCardFocus }))).toEqual({ opacity: '1', hovered: true, scoped: 'true' })
  expect(await card.evaluate(el => getComputedStyle(el).transform)).toBe('none')
  const after = await card.boundingBox()
  for (const dimension of ['x', 'y', 'width', 'height'] as const) expect(Math.abs(after![dimension] - before![dimension])).toBeLessThan(1)
  expect(await card.evaluate(el => getComputedStyle(el, '::after').pointerEvents)).toBe('none')
  expect(await card.evaluate(el => Math.abs(parseFloat(getComputedStyle(el, '::after').width) - el.clientWidth))).toBeLessThan(1)
  const frame = await card.evaluate(el => getComputedStyle(el, '::after').boxShadow)
  expect(frame).toContain('inset')
  await page.mouse.move(0, 0)
  await expect.poll(() => opacity(card)).toBe('0')
}

test('public cards share stable themed feedback across all page families', async ({ page }) => {
  test.setTimeout(240_000)
  const { article, project, book } = await seed(page)
  await page.setViewportSize({ width: 1440, height: 1000 })
  const routes: [string, string[]][] = [
    ['/', ['.sys-panel', '.home-note', '.knowledge-node']],
    ['/articles', ['.articles-filters', '.article-list-row']],
    ['/projects', ['.projects-lead', '.project-ledger-row']],
    ['/books', ['.books-current', '.book-ledger-row']],
    ['/about', ['.sys-panel', '.ae-domain', '.ae-panel', '.ae-channels a', '.ae-site dl > div']],
    ['/archive', ['.archive-row']],
    ['/search?q=CardFocus', ['.search-result']],
    ['/search?q=NoCardFocusMatch987654321', ['.search-state-row']],
    ['/articles?category=NoCardFocusMatch987654321', ['.empty-state']],
    [article.public_path, ['.content-toc-desktop', '.article-context-link']],
    [project.public_path, ['.related-note']],
    [book.public_path, ['.content-toc-desktop']],
    ['/missing-card-focus-page', ['.error-action']],
  ]
  for (const theme of ['light', 'dark']) {
    for (const [route, selectors] of routes) {
      await page.goto(route)
      if (!route.startsWith('/missing')) await expectHydrated(page)
      await page.evaluate(() => document.fonts.ready)
      await expect(page.locator('html')).toHaveAttribute('data-public-card-focus', 'true')
      await page.evaluate(value => { document.documentElement.classList.toggle('dark', value === 'dark') }, theme)
      for (const selector of selectors) await checkCard(page, page.locator(selector).first())
      if (route === '/archive') {
        const connector = page.locator('.archive-row-connector').first()
        await expect(connector).toBeVisible()
        expect(await connector.evaluate(el => getComputedStyle(el).width)).toBe('36px')
      }
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    }
  }
  await page.goto('/')
  await expectHydrated(page)
  await expect(page.getByTestId('home-atlas')).toHaveAttribute('aria-busy', 'false')
  await page.mouse.move(0, 0)
  const node = page.getByTestId('atlas-node').first()
  await node.hover()
  await expect.poll(() => opacity(page.getByTestId('atlas-article').first())).toBe('1')
  await expect.poll(() => opacity(page.getByTestId('home-atlas'))).toBe('0')
  await expect(page.locator('.knowledge-lines g[data-active="true"]').first()).toBeVisible()
  const link = page.getByTestId('atlas-article').first()
  const href = await link.getAttribute('href')
  await link.click()
  await expect(page).toHaveURL(new RegExp(`${href}$`))
})

test('card feedback supports keyboard reduced motion and touch without hover residue', async ({ page, browser }) => {
  await page.goto('/about')
  await expectHydrated(page)
  const card = page.locator('.ae-channels a').last()
  await card.focus()
  await expect.poll(() => opacity(card)).toBe('1')
  expect(await card.evaluate(el => getComputedStyle(el, '::after').transitionDuration)).toBe('0s')
  await page.keyboard.press('Tab')
  await expect.poll(() => opacity(card)).toBe('0')
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await card.hover()
  await expect.poll(() => opacity(card)).toBe('1')
  expect(await card.evaluate(el => getComputedStyle(el, '::after').transitionDuration)).toBe('0s')
  await page.mouse.move(0, 0)
  await expect.poll(() => opacity(card)).toBe('0')
  const context = await browser.newContext({ baseURL: new URL(page.url()).origin, viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true })
  try {
    const mobile = await context.newPage()
    await mobile.goto('/about')
    await expectHydrated(mobile)
    await mobile.evaluate(async () => { await document.fonts.ready; document.documentElement.style.scrollBehavior = 'auto' })
    const staticCard = mobile.locator('.ae-domain').first()
    await staticCard.tap()
    await expect.poll(() => opacity(staticCard)).toBe('0')
    expect(await staticCard.getAttribute('tabindex')).toBeNull()
    const rss = mobile.locator('.ae-channels a').last()
    await rss.evaluate(el => el.scrollIntoView({ behavior: 'instant', block: 'center' }))
    const rect = (await rss.boundingBox())!
    const cdp = await context.newCDPSession(mobile)
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: rect.x + 10, y: rect.y + 10 }] })
    await expect.poll(() => opacity(rss)).toBe('1')
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchCancel', touchPoints: [] })
    await expect.poll(() => opacity(rss)).toBe('0')
    expect(await mobile.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  }
  finally { await context.close() }
})

test('all writing desk routes exclude public feedback including shared previews', async ({ page }) => {
  const { article, project, book } = await seed(page)
  const routes = [
    '/admin', '/admin/login', '/admin/articles', '/admin/articles/new',
    `/admin/articles/${article.id}/edit`, `/admin/articles/${article.id}/preview`, `/admin/articles/${article.id}/revisions`,
    '/admin/projects', '/admin/projects/new', `/admin/projects/${project.id}/edit`,
    '/admin/books', '/admin/books/new', `/admin/books/${book.id}/edit`,
    '/admin/profile', '/admin/taxonomy', '/admin/media', '/admin/content', '/admin/assistant',
    '/admin/about', '/admin/about/preview', '/admin/about/revisions', '/admin/missing-card-focus-page',
  ]
  for (const route of routes) {
    await page.goto(route)
    await expect(page.locator('html')).not.toHaveAttribute('data-public-card-focus', 'true')
    for (const card of await page.locator('[data-focus-card]:visible').all()) {
      await card.hover()
      expect(await card.evaluate(el => getComputedStyle(el, '::after').content)).toBe('none')
    }
  }
  await page.goto('/')
  await page.locator('a[href="/admin/articles"]').first().click()
  await expect(page.locator('html')).not.toHaveAttribute('data-public-card-focus', 'true')
  await page.goBack()
  await expect(page.locator('html')).toHaveAttribute('data-public-card-focus', 'true')
  await checkCard(page, page.locator('.sys-panel'))
})

test('pointer spotlight follows public cards and clears across input and route changes', async ({ page, browser }) => {
  test.setTimeout(240_000)
  const { article, project, book } = await seed(page)
  await page.setViewportSize({ width: 1440, height: 1000 })
  const routes: [string, string][] = [
    ['/', '.sys-panel'], ['/articles', '.article-list-row'], ['/projects', '.projects-lead'],
    ['/books', '.books-current'], ['/about', '.ae-site dl > div'], ['/archive', '.archive-row'],
    ['/search?q=CardFocus', '.search-result'], [article.public_path, '.content-toc-desktop'],
    [project.public_path, '.related-note'], [book.public_path, '.content-toc-desktop'],
    ['/missing-card-glow', '.error-action'],
  ]
  for (const theme of ['light', 'dark']) {
    for (const [route, selector] of routes) {
      await page.goto(route)
      if (!route.startsWith('/missing')) await expectHydrated(page)
      await page.evaluate(async (value) => {
        await document.fonts.ready
        document.documentElement.style.scrollBehavior = 'auto'
        document.documentElement.classList.toggle('dark', value === 'dark')
      }, theme)
      await checkGlow(page, page.locator(selector).first())
    }
  }
  await page.goto('/')
  await expectHydrated(page)
  await expect(page.getByTestId('home-atlas')).toHaveAttribute('aria-busy', 'false')
  const node = page.getByTestId('atlas-node').first()
  await node.hover()
  await expect(page.locator('[data-focus-glow]')).toHaveCount(0)
  const branch = page.locator('.knowledge-path').first()
  await expect.poll(() => branch.evaluate(el => getComputedStyle(el, '::after').opacity)).toBe('1')
  const original = await branch.evaluate(el => getComputedStyle(el, '::after').transform)
  await node.hover({ position: { x: 20, y: 20 } })
  await expect.poll(() => branch.evaluate(el => getComputedStyle(el, '::after').transform)).not.toBe(original)

  await page.goto('/about')
  await expectHydrated(page)
  const nested = page.locator('.ae-site dl > div').first()
  await page.evaluate(async () => { await document.fonts.ready; document.documentElement.style.scrollBehavior = 'auto' })
  await checkGlow(page, nested)
  await nested.hover()
  await expect(nested).toHaveAttribute('data-focus-glow', '')
  await expect(page.locator('[data-focus-glow]')).toHaveCount(1)
  await page.keyboard.press('Tab')
  await expect(page.locator('[data-focus-glow]')).toHaveCount(0)
  await checkGlow(page, nested)
  await nested.hover()
  await expect(nested).toHaveAttribute('data-focus-glow', '')
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await expect(page.locator('[data-focus-glow]')).toHaveCount(0)
  await nested.hover({ position: { x: 10, y: 10 } })
  expect(await nested.evaluate(el => getComputedStyle(el, '::after').backgroundImage)).toBe('none')
  await page.emulateMedia({ reducedMotion: 'no-preference' })
  await nested.hover()
  await expect(nested).toHaveAttribute('data-focus-glow', '')
  await page.locator('a[href="/admin/articles"]').first().click()
  await expect(page.locator('html')).not.toHaveAttribute('data-public-card-focus', 'true')
  await expect(page.locator('[data-focus-glow]')).toHaveCount(0)
  await page.goto('/admin/about/preview')
  await expectHydrated(page)
  for (const card of await page.locator('[data-focus-card]:visible').all()) {
    await card.hover()
    await expect(card).not.toHaveAttribute('data-focus-glow', '')
  }
  const context = await browser.newContext({ baseURL: new URL(page.url()).origin, viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true })
  try {
    const mobile = await context.newPage()
    await mobile.goto('/about')
    await expectHydrated(mobile)
    await mobile.locator('.ae-domain').first().tap()
    await expect(mobile.locator('[data-focus-glow]')).toHaveCount(0)
  }
  finally { await context.close() }
})
