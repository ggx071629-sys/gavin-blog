import { expect, test } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

test('desktop readers can enter the authenticated writing desk from the public header', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  const articleEnhancerRequests: string[] = []
  page.on('request', (request) => {
    if (/highlight\.js|mermaid|katex|markdown-it-texmath/i.test(request.url())) {
      articleEnhancerRequests.push(request.url())
    }
  })
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  expect(articleEnhancerRequests, 'homepage article enhancer requests').toEqual([])

  const writingDeskLink = page.getByRole('link', { name: '写作台', exact: true })
  await expect(writingDeskLink).toBeVisible()
  await expect(writingDeskLink).toHaveAttribute('href', '/admin/articles')

  const headerActionMetrics = await page.locator('.site-header .site-nav-action:visible').evaluateAll(elements => (
    elements.map((element) => {
      const style = getComputedStyle(element)
      return {
        height: element.getBoundingClientRect().height,
        fontSize: style.fontSize,
      }
    })
  ))
  expect(headerActionMetrics).toHaveLength(6)
  expect(Math.min(...headerActionMetrics.map(metric => metric.height))).toBeGreaterThanOrEqual(44)
  expect(Math.min(...headerActionMetrics.map(metric => parseFloat(metric.fontSize)))).toBeGreaterThanOrEqual(14)

  await writingDeskLink.click()

  await expect(page).toHaveURL(/\/admin\/login\?returnTo=\/admin\/articles$/)
  await expect(page.getByRole('heading', { name: '登录写作台' })).toBeVisible()
})

test('mobile readers can navigate, switch theme, and skip to content', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)

  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: '跳到正文' })).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.locator('#main-content')).toBeFocused()

  const themeButton = page.getByRole('button', { name: '切换颜色主题' })
  const wasDark = await page.locator('html').evaluate(element => element.classList.contains('dark'))
  await themeButton.click()
  await expect(page.locator('html')).toHaveClass(wasDark ? /^(?!.*\bdark\b).*$/ : /dark/)

  const menuButton = page.getByRole('button', { name: '打开主导航菜单' })
  await expect(menuButton).toHaveAttribute('aria-expanded', 'false')
  await menuButton.click()
  await expect(page.getByRole('navigation', { name: '移动端主导航' })).toBeVisible()
  await expect(page.getByRole('link', { name: '归档', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: '关于', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: '写作台', exact: true })).toHaveAttribute('href', '/admin/articles')

  await page.getByRole('link', { name: '文章', exact: true }).focus()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('navigation', { name: '移动端主导航' })).toBeHidden()
  await expect(menuButton).toHaveAttribute('aria-expanded', 'false')
  await expect(menuButton).toBeFocused()

  await menuButton.click()

  await page.getByRole('link', { name: '关于', exact: true }).click()
  await expect(page).toHaveURL(/\/about$/)
  const profileResponse = await page.request.get('/api/v1/profile')
  expect(profileResponse.ok()).toBe(true)
  const profile = await profileResponse.json()
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(`你好，我是 ${profile.name || 'Gavin'}。`)
  await expect(page.getByRole('button', { name: '打开主导航菜单' })).toHaveAttribute('aria-expanded', 'false')

  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await page.getByRole('button', { name: '打开主导航菜单' }).click()
  await page.getByRole('link', { name: '写作台', exact: true }).click()
  await expect(page).toHaveURL(/\/admin\/login\?returnTo=\/admin\/articles$/)
})

const expectNoHorizontalOverflow = async (page: import('@playwright/test').Page, label: string) => {
  const overflow = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }))
  expect(overflow.scrollWidth, label).toBeLessThanOrEqual(overflow.clientWidth)
}

const failListRequest = (page: import('@playwright/test').Page, endpoint: string) => page.route(endpoint, route => route.fulfill({
  status: 503,
  contentType: 'application/json',
  body: JSON.stringify({ detail: '受控故障' }),
}))

test('public navigation failure renders a recoverable error page instead of the stale page', async ({ page }) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)

  const articlesEndpoint = '**/api/v1/articles*'
  await failListRequest(page, articlesEndpoint)
  await page.getByRole('link', { name: '文章', exact: true }).first().click()

  await expect(page).toHaveURL(/\/articles$/)
  await expect(page.locator('.error-stage')).toBeVisible()
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('服务暂时不可用')
  await expect(page.getByRole('button', { name: /重试当前页面/ })).toBeVisible()
  await expect(page.getByTestId('home-hero')).toHaveCount(0)

  await page.unroute(articlesEndpoint)
  await page.getByRole('button', { name: /重试当前页面/ }).click()
  await expectHydrated(page)
  await expect(page.getByTestId('articles-results')).toBeVisible()
  await expect(page.locator('.error-stage')).toHaveCount(0)
})

test('error page recovery entries clear the failure and reach the target route', async ({ page }) => {
  await page.goto('/about', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)

  const booksEndpoint = '**/api/v1/books*'
  await failListRequest(page, booksEndpoint)
  await page.getByRole('link', { name: '读书', exact: true }).first().click()

  await expect(page).toHaveURL(/\/books$/)
  await expect(page.locator('.error-stage')).toBeVisible()
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('服务暂时不可用')

  await page.unroute(booksEndpoint)
  await page.getByRole('link', { name: /浏览文章/ }).click()
  await expect(page).toHaveURL(/\/articles$/)
  await expect(page.getByRole('heading', { level: 1 })).toContainText('开发过程与问题排查')
  await expect(page.locator('.error-stage')).toHaveCount(0)
})

test('search failure keeps the query and recovers through retry', async ({ page }) => {
  await page.goto('/search', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)

  const searchEndpoint = '**/api/v1/search*'
  await failListRequest(page, searchEndpoint)
  await page.getByTestId('search-input').fill('封面契约')
  await page.getByTestId('search-submit').click()

  await expect(page).toHaveURL(/\/search\?q=/)
  await expect(page.locator('.error-stage')).toBeVisible()
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('服务暂时不可用')

  await page.unroute(searchEndpoint)
  await page.getByRole('button', { name: /重试当前页面/ }).click()
  await expectHydrated(page)
  await expect(page.getByTestId('search-input')).toHaveValue('封面契约')
  await expect(page.getByTestId('search-count')).toBeVisible()
})

test('mobile overlay dialog traps focus, locks background, and clears at 1280', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)

  const menuButton = page.getByRole('button', { name: '打开主导航菜单' })
  await menuButton.click()

  const dialog = page.getByRole('dialog', { name: '主导航' })
  await expect(dialog).toBeVisible()
  await expect(dialog).toHaveAttribute('aria-modal', 'true')
  await expect(page.getByRole('navigation', { name: '移动端主导航' })).toBeVisible()
  await expect(page.locator('.site-header-bar')).toHaveJSProperty('inert', true)
  await expect(page.locator('#main-content')).toHaveJSProperty('inert', true)
  await expect.poll(() => page.evaluate(() => document.body.style.overflow)).toBe('hidden')

  const closeButton = dialog.getByRole('button', { name: '关闭主导航菜单' })
  await expect(closeButton).toBeFocused()
  await page.keyboard.press('Shift+Tab')
  await expect(page.getByRole('link', { name: '写作台', exact: true })).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(closeButton).toBeFocused()

  await page.getByTestId('site-menu-backdrop').click({ position: { x: 8, y: 8 } })
  await expect(dialog).toBeHidden()
  await expect(page.locator('#main-content')).toHaveJSProperty('inert', false)
  await expect.poll(() => page.evaluate(() => document.body.style.overflow)).toBe('')
  await expect(menuButton).toBeFocused()

  await menuButton.click()
  await expect(dialog).toBeVisible()
  await page.setViewportSize({ width: 1280, height: 800 })
  await expect(dialog).toBeHidden()
  await expect(page.locator('#main-content')).toHaveJSProperty('inert', false)
  await expect(page.getByRole('navigation', { name: '主导航' })).toBeVisible()
})

test('mobile menu switches from a full-screen route index to the tablet drawer at 640', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.setViewportSize({ width: 639, height: 800 })
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)

  const menuButton = page.getByRole('button', { name: '打开主导航菜单' })
  await menuButton.click()

  const backdrop = page.getByTestId('site-menu-backdrop')
  const overlay = page.getByTestId('site-menu-overlay')
  const primaryNavigation = page.getByTestId('site-menu-primary-navigation')
  const writingDesk = page.getByTestId('site-menu-writing-desk')

  await expect(overlay).toBeVisible()
  await expect(overlay.getByText('G / NOTES', { exact: true })).toBeVisible()
  await expect(overlay.getByText('主导航', { exact: true })).toBeVisible()
  await expect(primaryNavigation.locator('[data-menu-route]')).toHaveCount(6)
  const routes = [
    { href: '/articles', label: '文章' },
    { href: '/projects', label: '项目' },
    { href: '/books', label: '读书' },
    { href: '/archive', label: '归档' },
    { href: '/about', label: '关于' },
    { href: '/search', label: '搜索' },
  ]
  expect(await primaryNavigation.locator('[data-menu-route]').evaluateAll(elements => elements.map(element => element.getAttribute('href')))).toEqual(routes.map(route => route.href))
  for (const route of routes) await expect(primaryNavigation.getByRole('link', { name: route.label, exact: true })).toHaveAttribute('href', route.href)
  await expect(writingDesk).toHaveAttribute('href', '/admin/articles')

  const compactMetrics = await page.evaluate(() => {
    const viewport = { width: window.innerWidth, height: window.innerHeight }
    const backdropElement = document.querySelector<HTMLElement>('[data-testid="site-menu-backdrop"]')!
    const overlayElement = document.querySelector<HTMLElement>('[data-testid="site-menu-overlay"]')!
    const navigationElement = document.querySelector<HTMLElement>('[data-testid="site-menu-primary-navigation"]')!
    const brandElement = overlayElement.querySelector<HTMLElement>('.site-menu-brand')!
    const titleElement = overlayElement.querySelector<HTMLElement>('.site-menu-overlay-title')!
    const targetElements = [
      ...navigationElement.querySelectorAll<HTMLElement>('[data-menu-route]'),
      document.querySelector<HTMLElement>('[data-testid="site-menu-writing-desk"]')!,
      overlayElement.querySelector<HTMLElement>('button[aria-label="关闭主导航菜单"]')!,
    ]
    const rect = (element: HTMLElement) => {
      const bounds = element.getBoundingClientRect()
      return { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height }
    }
    return {
      viewport,
      backdrop: rect(backdropElement),
      overlay: rect(overlayElement),
      brand: rect(brandElement),
      title: rect(titleElement),
      navigation: rect(navigationElement),
      rowGap: getComputedStyle(navigationElement).rowGap,
      targetSizes: targetElements.map((element) => {
        const bounds = element.getBoundingClientRect()
        return { width: bounds.width, height: bounds.height }
      }),
      transitionProperties: [backdropElement, overlayElement].map(element => getComputedStyle(element).transitionProperty),
    }
  })

  expect(compactMetrics.backdrop).toEqual({ x: 0, y: 0, ...compactMetrics.viewport })
  expect(compactMetrics.overlay).toEqual({ x: 0, y: 0, ...compactMetrics.viewport })
  expect(compactMetrics.brand.y).toBeLessThan(compactMetrics.title.y)
  expect(compactMetrics.title.y).toBeLessThan(compactMetrics.navigation.y)
  expect(compactMetrics.navigation.y - compactMetrics.title.y - compactMetrics.title.height).toBeCloseTo(20, 0)
  expect(compactMetrics.rowGap).toBe('8px')
  expect(Math.min(...compactMetrics.targetSizes.map(({ width }) => width))).toBeGreaterThanOrEqual(44)
  expect(Math.min(...compactMetrics.targetSizes.map(({ height }) => height))).toBeGreaterThanOrEqual(44)
  expect(compactMetrics.transitionProperties).toEqual(['none', 'none'])

  await backdrop.click({ position: { x: 8, y: 8 } })
  await expect(overlay).toBeHidden()
  await expect(page.locator('.site-header-bar')).toHaveJSProperty('inert', false)
  await expect(menuButton).toBeFocused()

  await page.setViewportSize({ width: 640, height: 800 })
  await menuButton.click()
  const drawerMetrics = await overlay.evaluate((element) => {
    const bounds = element.getBoundingClientRect()
    return { x: bounds.x, width: bounds.width, right: bounds.right }
  })
  expect(drawerMetrics.x).toBeGreaterThan(0)
  expect(drawerMetrics.width).toBeLessThan(640)
  expect(drawerMetrics.right).toBe(640)
})

test('closed overlay does not restore a stale scroll lock on later query changes', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/about', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)

  await page.evaluate(() => window.scrollTo(0, 360))
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(200)

  const menuButton = page.getByRole('button', { name: '打开主导航菜单' })
  await menuButton.click()
  const dialog = page.getByRole('dialog', { name: '主导航' })
  await expect(dialog).toBeVisible()
  await dialog.getByRole('button', { name: '关闭主导航菜单' }).click()
  await expect(dialog).toBeHidden()

  await page.evaluate(() => window.scrollTo(0, 80))
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeLessThan(150)

  await page.goto('/about?from=overlay')
  await expectHydrated(page)
  const afterQuery = await page.evaluate(() => window.scrollY)
  expect(afterQuery, 'must not jump back to the overlay lock snapshot').toBeLessThan(150)
})

test('public chrome keeps one navigation sequence and prevents narrow overflow', async ({ page }) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)

  for (const width of [320, 360, 375, 390, 768, 1024, 1280, 1440] as const) {
    await page.setViewportSize({ width, height: 900 })
    await expectNoHorizontalOverflow(page, `${width} overflow`)
    if (width < 1280) {
      await expect(page.getByRole('button', { name: '打开主导航菜单' })).toBeVisible()
      await expect(page.getByRole('navigation', { name: '主导航' })).toHaveCount(0)
    }
    else {
      await expect(page.getByRole('navigation', { name: '主导航' })).toBeVisible()
      await expect(page.getByRole('button', { name: '打开主导航菜单' })).toHaveCount(0)
    }
  }
})

test('homepage keeps product copy, dual CTAs, profile, and empty-state without a Now block', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)

  await expect(page.getByTestId('home-hero').getByRole('heading', { level: 1 })).toHaveText('开发笔记、项目记录，还有读书心得。')
  const profileResponse = await page.request.get('/api/v1/profile')
  expect(profileResponse.ok()).toBe(true)
  const profile = await profileResponse.json()
  await expect(page.getByTestId('profile-card').getByRole('heading', { name: profile.name, exact: true })).toBeVisible()
  await expect(page.locator('.notebook-actions').getByRole('link', { name: /浏览文章/ })).toHaveAttribute('href', '/articles')
  await expect(page.locator('.notebook-actions').getByRole('link', { name: /查看项目/ })).toHaveAttribute('href', '/projects')
  await expect(page.getByRole('link', { name: '写作台', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: '切换颜色主题' })).toBeVisible()
  await expect(page.getByTestId('profile-card')).toBeVisible()
  await expect(page.getByTestId('home-latest')).toHaveAttribute('aria-busy', 'false')
  const articleCards = page.getByTestId('home-featured').or(page.getByTestId('home-note-row'))
  const emptyState = page.getByText('第一篇文章正在路上。')
  if (await articleCards.count()) {
    await expect(articleCards.first()).toBeVisible()
  }
  else {
    await expect(emptyState).toBeVisible()
  }
  await expect(page.locator('body')).not.toContainText('Systems, stories')
  await expect(page.getByTestId('home-now')).toHaveCount(0)
})

test('homepage lists seeded public articles from the real API', async ({ page }) => {
  await page.goto('/admin/login', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)

  const csrf = (await page.context().cookies()).find(cookie => cookie.name === 'gavin_csrf')?.value
  expect(csrf).toBeTruthy()
  const headers = { 'X-CSRF-Token': csrf! }

  for (const item of [
    { title: '壳层种子文章一', slug: 'chrome-home-seed-1' },
    { title: '壳层种子文章二', slug: 'chrome-home-seed-2' },
    { title: '壳层种子文章三', slug: 'chrome-home-seed-3' },
  ]) {
    const created = await page.request.post('/api/v1/admin/articles', {
      headers,
      data: {
        title: item.title,
        slug: item.slug,
        summary: '隔离测试种子摘要',
        content: `# ${item.title}\n\n真实 API 种子正文。`,
      },
    })
    expect(created.status()).toBe(201)
    const article = await created.json()
    const published = await page.request.post(`/api/v1/admin/articles/${article.id}/publish`, {
      headers,
      data: { version: article.version },
    })
    expect(published.ok()).toBeTruthy()
  }

  const listed = await page.request.get('/api/v1/articles?limit=4&offset=0')
  expect(listed.ok()).toBeTruthy()
  const articles = await listed.json() as { title: string, public_path: string }[]
  expect(articles.some(article => article.title === '壳层种子文章一')).toBeTruthy()
  expect(articles.some(article => article.title === '壳层种子文章二')).toBeTruthy()
  expect(articles.some(article => article.title === '壳层种子文章三')).toBeTruthy()

  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await expect(page.getByTestId('home-featured')).toBeVisible()
  await expect(page.getByTestId('home-note-row')).toHaveCount(articles.length - 1)
  for (const article of articles) {
    await expect(page.getByTestId('home-latest').getByRole('heading').filter({ hasText: article.title }).getByRole('link')).toHaveAttribute('href', article.public_path)
  }
  await expect(page.getByTestId('home-latest')).toContainText('壳层种子文章一')
  await expect(page.getByTestId('home-latest')).toContainText('壳层种子文章二')
  await expect(page.getByTestId('home-latest')).toContainText('壳层种子文章三')
  await expect(page.getByText('第一篇文章正在路上。')).toHaveCount(0)
  await expect(page.getByTestId('profile-card')).toBeVisible()
})
