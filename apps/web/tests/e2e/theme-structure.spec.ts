import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { expectHydrated as waitForHydration } from '../support/hydration'

const setTheme = async (page: Page, theme: 'light' | 'dark') => {
  const html = page.locator('html')
  const isDark = await html.evaluate(element => element.classList.contains('dark'))

  if (isDark !== (theme === 'dark')) {
    await page.getByRole('button', { name: '切换颜色主题' })
      .or(page.getByTestId('admin-theme-toggle'))
      .filter({ visible: true })
      .first()
      .click()
  }

  await expect(html).toHaveClass(theme === 'dark' ? /dark/ : /^(?!.*\bdark\b).*$/)
  await page.evaluate(() => document.fonts.ready)
}

const publishHomepageFixtures = async (page: Page) => {
  await page.goto('/admin/login', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)

  const csrf = (await page.context().cookies()).find(cookie => cookie.name === 'gavin_csrf')?.value
  expect(csrf).toBeTruthy()

  for (let index = 0; index < 2; index += 1) {
    const created = await page.request.post('/api/v1/admin/articles', {
      headers: { 'X-CSRF-Token': csrf! },
      data: {
        title: `主题结构验证文章 ${index + 1}`,
        slug: `theme-structure-${index + 1}`,
        summary: '用于验证浅色与暗色共享页面结构。',
        content: '# 主题结构\n\n结构应独立于颜色主题。',
      },
    })
    expect(created.status()).toBe(201)
    const article = await created.json()
    const published = await page.request.post(`/api/v1/admin/articles/${article.id}/publish`, {
      headers: { 'X-CSRF-Token': csrf! },
      data: { version: article.version },
    })
    expect(published.ok()).toBeTruthy()
  }
}

const readHomepageStructure = (page: Page) => page.evaluate(() => {
  const styles = (selector: string) => {
    const element = document.querySelector<HTMLElement>(selector)
    if (!element) throw new Error(`Missing homepage element: ${selector}`)
    const style = getComputedStyle(element)
    const rect = element.getBoundingClientRect()
    return {
      display: style.display,
      borderTopWidth: style.borderTopWidth,
      gridColumn: style.gridColumn,
      gridRow: style.gridRow,
      marginTop: style.marginTop,
      left: Math.round(rect.left),
      top: Math.round(rect.top),
      bottom: Math.round(rect.bottom),
    }
  }
  const root = getComputedStyle(document.documentElement)

  return {
    firstArticle: styles('.home-featured'),
    opening: styles('.home-opening'),
    lead: styles('.notebook-hero'),
    pair: styles('.home-hero-pair-grid'),
    atlas: styles('[data-testid="home-atlas"]'),
    profile: styles('[data-testid="profile-card"]'),
    radius: root.getPropertyValue('--ee-radius').trim(),
    radiusSoft: root.getPropertyValue('--ee-radius-soft').trim(),
    recent: styles('.home-notes'),
    shadow: root.getPropertyValue('--ee-floating-shadow').trim(),
  }
})

const readArticleListStructure = (page: Page) => page.locator('.article-list-row').first().evaluate((element) => {
  const style = getComputedStyle(element)
  const transparent = (value: string) => value === 'transparent' || value === 'rgba(0, 0, 0, 0)'
  return {
    flexDirection: style.flexDirection,
    flexWrap: style.flexWrap,
    borderLeftVisible: Number.parseFloat(style.borderLeftWidth) > 0 && !transparent(style.borderLeftColor),
    borderRightVisible: Number.parseFloat(style.borderRightWidth) > 0 && !transparent(style.borderRightColor),
    hasDate: Boolean(element.querySelector('.article-info-strip time')),
    hasTitle: Boolean(element.querySelector('.article-list-title')),
    hasMeta: Boolean(element.querySelector('.article-info-duration')),
  }
})

const readAdminLoginStructure = (page: Page) => page.evaluate(() => {
  const read = (testId: string) => {
    const element = document.querySelector<HTMLElement>(`[data-testid="${testId}"]`)
    if (!element) throw new Error(`Missing admin login element: ${testId}`)
    const rect = element.getBoundingClientRect()
    const style = getComputedStyle(element)
    return {
      display: style.display,
      height: Math.round(rect.height),
      left: Math.round(rect.left),
      top: Math.round(rect.top),
      width: Math.round(rect.width),
    }
  }

  return {
    form: read('admin-login-form'),
    shell: read('admin-login-shell'),
    stage: read('admin-login-form-stage'),
    surface: read('admin-login-form-surface'),
  }
})

test('login', async ({ page }, info) => {
  test.setTimeout(180_000)
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  page.on('console', message => { if (['warning', 'error'].includes(message.type())) errors.push(message.text()) })
  for (const width of [320, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: width === 320 ? 480 : 900 })
    const structures = []
    for (const theme of ['light', 'dark'] as const) {
      await page.goto('/admin/login', { waitUntil: 'domcontentloaded' })
      await waitForHydration(page)
      await setTheme(page, theme)
      await expect(page.getByTestId('username')).toHaveCSS('color', theme === 'dark' ? 'rgb(240, 243, 250)' : 'rgb(8, 12, 21)')
      await expect(page.getByTestId('username')).toHaveCSS('background-color', theme === 'dark' ? 'rgb(16, 20, 30)' : 'rgb(255, 255, 255)')
      await expect(page.getByTestId('login')).toHaveCSS('color', theme === 'dark' ? 'rgb(16, 27, 48)' : 'rgb(255, 255, 255)')
      await expect(page.getByTestId('login')).toHaveCSS('background-color', theme === 'dark' ? 'rgb(125, 170, 255)' : 'rgb(0, 93, 255)')
      await expect(page.getByTestId('admin-login-brand-panel')).toHaveCount(0)
      await expect(page.getByRole('heading', { name: '登录写作台', level: 1 })).toBeVisible()
      await expect(page.getByRole('link', { name: '返回 Gavin' })).toHaveAttribute('href', '/')
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1)
      structures.push(await readAdminLoginStructure(page))
      const violations = (await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()).violations
      expect(violations).toEqual([])
      await page.screenshot({ path: info.outputPath(`${theme[0]}${width}.png`), fullPage: true })
    }
    expect(structures[1], `${width} structure changes with theme`).toEqual(structures[0])
    const structure = structures[0]!
    const formWidth = Math.min(430, width - (width <= 360 ? 36 : 44))
    expect(structure.shell).toMatchObject({ left: 0, top: 0, width })
    expect(structure.stage).toMatchObject({ left: 0, width })
    expect(structure.surface).toMatchObject({ left: (width - formWidth) / 2, width: formWidth })
    expect(structure.form.width).toBe(formWidth)
  }
  await page.goto('/admin/login?returnTo=%2Fadmin%2Fbooks')
  await waitForHydration(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('password').press('Enter')
  await expect(page).toHaveURL(/\/admin\/books$/)
  expect(errors).toEqual([])
})

test('desktop homepage and article list share the dark canonical structure', async ({ page }) => {
  test.setTimeout(180_000)
  await page.setViewportSize({ width: 1280, height: 900 })
  await publishHomepageFixtures(page)

  await page.goto('/', { waitUntil: 'networkidle' })
  await setTheme(page, 'light')
  const lightHome = await readHomepageStructure(page)
  await setTheme(page, 'dark')
  const darkHome = await readHomepageStructure(page)

  expect(lightHome).toMatchObject({
    firstArticle: { borderTopWidth: '1px' },
    opening: { display: 'block' },
    pair: { display: 'grid' },
    radius: '4px',
    radiusSoft: '8px',
  })
  expect(lightHome.atlas.left).toBe(lightHome.lead.left)
  expect(lightHome.profile.left).toBeGreaterThan(lightHome.atlas.left)
  expect(lightHome.atlas.top).toBeGreaterThanOrEqual(lightHome.lead.bottom)
  expect(lightHome.recent.top).toBeGreaterThan(Math.max(lightHome.lead.bottom, lightHome.atlas.bottom))
  expect(lightHome.shadow).toContain('0 18px 45px')
  expect(darkHome.shadow).toContain('0 18px 45px')
  expect({ ...lightHome, shadow: null }).toEqual({ ...darkHome, shadow: null })

  await page.goto('/articles', { waitUntil: 'networkidle' })
  await setTheme(page, 'light')
  const lightList = await readArticleListStructure(page)
  await setTheme(page, 'dark')
  const darkList = await readArticleListStructure(page)

  expect(lightList).toEqual({
    flexDirection: 'row',
    flexWrap: 'nowrap',
    borderLeftVisible: true,
    borderRightVisible: true,
    hasDate: true,
    hasTitle: true,
    hasMeta: true,
  })
  expect(lightList).toEqual(darkList)
})

test('mobile article list stacks card content with date, title and reading time', async ({ page }) => {
  test.setTimeout(180_000)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/admin/login', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  const csrf = (await page.context().cookies()).find(cookie => cookie.name === 'gavin_csrf')?.value
  const created = await page.request.post('/api/v1/admin/articles', {
    headers: { 'X-CSRF-Token': csrf! },
    data: {
      title: '主题结构移动列表',
      slug: `theme-structure-mobile-${Date.now()}`,
      summary: '移动列表行。',
      content: '# 列表\n\n行节奏。',
    },
  })
  expect(created.status()).toBe(201)
  const article = await created.json()
  const published = await page.request.post(`/api/v1/admin/articles/${article.id}/publish`, {
    headers: { 'X-CSRF-Token': csrf! },
    data: { version: article.version },
  })
  expect(published.ok()).toBeTruthy()
  await page.goto('/articles', { waitUntil: 'networkidle' })
  const list = await readArticleListStructure(page)
  expect(list).toMatchObject({
    flexDirection: 'column',
    flexWrap: 'nowrap',
    hasDate: true,
    hasTitle: true,
    hasMeta: true,
  })
})

test('representative public and admin pages remain overflow-free on mobile in both themes', async ({ page }) => {
  test.setTimeout(180_000)
  await page.setViewportSize({ width: 390, height: 844 })
  const routes = ['/', '/articles', '/projects', '/books', '/archive', '/about', '/search', '/admin/login']

  for (const route of routes) {
    for (const theme of ['light', 'dark'] as const) {
      await page.goto(route, { waitUntil: 'domcontentloaded' })
      await waitForHydration(page)
      await setTheme(page, theme)
      const width = await page.evaluate(() => ({
        client: document.documentElement.clientWidth,
        scroll: document.documentElement.scrollWidth,
      }))
      expect(width.scroll, `${route} ${theme} horizontal overflow`).toBeLessThanOrEqual(width.client)
    }
  }
})
