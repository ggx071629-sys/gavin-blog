import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { expectHydrated } from '../support/hydration'

const open = async (page: Page, path: string) => {
  await page.goto(path)
  await expectHydrated(page)
  await expect(page.getByRole('heading', { level: 1 })).toHaveCount(1)
}

async function coverage(page: Page, info: import('@playwright/test').TestInfo, responsive = false) {
  test.setTimeout(600_000)
  const errors: string[] = []
  const checks: unknown[] = []
  const matrix = async (index: number) => {
    for (const dark of [false, true]) {
      await page.setViewportSize({ width: 1440, height: 1000 })
      if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== dark) await page.getByRole('button', { name: '切换颜色主题' }).filter({ visible: true }).click()
      for (const width of [1440, 1280, 1024, 768, 390, 320]) {
        await page.setViewportSize({ width, height: 900 })
        await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1)
        await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
        checks.push({ index, dark, width })
        if (width === 390 && dark) await page.screenshot({ path: info.outputPath(`${index}.png`), fullPage: true, animations: 'disabled' })
      }
      const scope = index === 0 ? '.admin-login-shell' : '#admin-main'
      await expect.poll(() => page.evaluate(selector => document.getAnimations().filter(animation => animation instanceof CSSTransition && animation.playState === 'running' && animation.effect instanceof KeyframeEffect && animation.effect.target instanceof Element && animation.effect.target.closest(selector)).length, scope)).toBe(0)
      expect((await new AxeBuilder({ page }).include(scope).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()).violations).toEqual([])
    }
    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.getByRole('button', { name: '切换颜色主题' }).filter({ visible: true }).click()
  }
  page.on('pageerror', error => errors.push(error.message))
  await page.setViewportSize({ width: 1440, height: 1000 })
  await open(page, '/admin/login')
  if (await page.locator('html').evaluate(el => el.classList.contains('dark'))) await page.getByRole('button', { name: '切换颜色主题' }).click()
  await expect(page.getByTestId('username')).toBeVisible()
  await page.screenshot({ path: info.outputPath('login.png'), fullPage: true })
  if (responsive) await matrix(0)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  const headers = { 'X-CSRF-Token': (await page.context().cookies()).find(c => c.name === 'gavin_csrf')!.value }
  const ids: Record<string, number> = {}
  for (const kind of ['articles', 'books', 'projects']) {
    const created = await page.request.post(`/api/v1/admin/${kind}`, { headers, data: { title: '界面交付核对', book_title: '阅读与实践', author: 'Gavin', slug: `coverage-${kind}-${Date.now()}`, content: '# 实践记录\n\n这是通过真实 API 保存的验收正文。' } })
    expect(created.status()).toBe(201)
    const value = await created.json()
    ids[kind] = value.id
    expect((await page.request.post(`/api/v1/admin/${kind}/${value.id}/publish`, { headers, data: { version: value.version } })).ok()).toBe(true)
  }
  const paths: [string, string][] = [
    ['articles', '/admin/articles'], ['article-new', '/admin/articles/new'], ['article-edit', `/admin/articles/${ids.articles}/edit`],
    ['article-preview', `/admin/articles/${ids.articles}/preview`], ['article-revisions', `/admin/articles/${ids.articles}/revisions`],
    ['books', '/admin/books'], ['book-new', '/admin/books/new'], ['book-edit', `/admin/books/${ids.books}/edit`],
    ['projects', '/admin/projects'], ['project-new', '/admin/projects/new'], ['project-edit', `/admin/projects/${ids.projects}/edit`],
    ['profile', '/admin/profile'], ['about', '/admin/about'], ['about-preview', '/admin/about/preview'], ['about-revisions', '/admin/about/revisions'],
    ['taxonomy', '/admin/taxonomy'], ['media', '/admin/media'], ['content', '/admin/content'], ['assistant', '/admin/assistant'],
  ]
  const records: unknown[] = [{ name: 'login', path: '/admin/login' }]
  for (const [name, path] of paths) {
    await open(page, path)
    await expect(page.locator('.admin-core-shell')).toHaveCSS('background-color', 'rgb(255, 255, 255)')
    await expect(page.locator('.admin-core-shell')).toHaveCSS('font-family', /Inter.*Noto Sans SC/)
    await expect(page.locator('.admin-sidebar')).toHaveCSS('width', '254px')
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1)
    await expect(page.locator('#admin-main')).toBeVisible()
    const title = await page.getByRole('heading', { level: 1 }).innerText()
    expect(title.trim()).not.toBe('')
    await page.screenshot({ path: info.outputPath(`${records.length}.png`), fullPage: true, animations: 'disabled' })
    records.push({ name, path, title })
    if (responsive) await matrix(records.length - 1)
  }
  expect(records).toHaveLength(20)
  await info.attach('coverage', { body: JSON.stringify({ viewport: [1440, 1000], theme: 'light', records, errors }), contentType: 'application/json' })
  expect(errors).toEqual([])
  if (responsive) {
    expect(checks).toHaveLength(240)
    await info.attach('matrix', { body: JSON.stringify({ checks, accessibilityScans: 40, errors }), contentType: 'application/json' })
  }
}

test('c', async ({ page }, info) => { await coverage(page, info) })
test('r', async ({ page }, info) => { await coverage(page, info, true) })

test('f', async ({ page }) => {
  await open(page, '/admin/login')
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('password').press('Enter')
  await expect(page).toHaveURL(/\/admin\/articles$/)
  for (const path of ['/', '/about', '/articles']) {
    await page.goto(path)
    await expectHydrated(page)
    for (const dark of [false, true]) {
      if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== dark) await page.getByRole('button', { name: '切换颜色主题' }).filter({ visible: true }).click()
      expect(await page.locator('main').evaluate(el => getComputedStyle(el).getPropertyValue('--studio-primary'))).toBe('')
      await expect(page.locator('.admin-core-shell')).toHaveCount(0)
    }
  }
  await open(page, '/admin/articles')
  await page.locator('.admin-sidebar').getByRole('button', { name: '退出', exact: true }).click()
  await expect(page).toHaveURL(/\/admin\/login/)
  await page.goto('/admin/articles/new')
  await expectHydrated(page)
  await expect(page).toHaveURL(/\/admin\/login\?returnTo=/)
  await expect(page.getByTestId('login')).toBeVisible()
  await expect(page.locator('.writing-workspace')).toHaveCount(0)
})
