import { expect, test, type Page } from '@playwright/test'
import { join } from 'node:path'
import { expectHydrated } from '../support/hydration'
import { groupArticlesByYear } from '../../utils/archive'
import { archiveDayStamp } from '../../utils/content'
import type { PublicArticle } from '../../types/api'

const loginAndCsrf = async (page: Page) => {
  await page.goto('/admin/login', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  const csrf = (await page.context().cookies()).find(cookie => cookie.name === 'gavin_csrf')?.value
  expect(csrf).toBeTruthy()
  return csrf!
}

const createCategory = async (page: Page, csrf: string, name: string, slug: string) => {
  const created = await page.request.post('/api/v1/admin/categories', {
    headers: { 'X-CSRF-Token': csrf },
    data: { name, slug },
  })
  expect(created.status(), name).toBe(201)
  return created.json()
}

const publishArticle = async (
  page: Page,
  csrf: string,
  title: string,
  slug: string,
  extras: { category_id?: number } = {},
) => {
  const created = await page.request.post('/api/v1/admin/articles', {
    headers: { 'X-CSRF-Token': csrf },
    data: {
      title,
      slug,
      summary: `${title} summary`,
      content: `# ${title}\n\n${'word '.repeat(80)}`,
      category_id: extras.category_id ?? null,
      tag_ids: [],
    },
  })
  expect(created.status(), title).toBe(201)
  const article = await created.json()
  const published = await page.request.post(`/api/v1/admin/articles/${article.id}/publish`, {
    headers: { 'X-CSRF-Token': csrf },
    data: { version: article.version },
  })
  expect(published.ok(), title).toBeTruthy()
  return article
}

test('empty archive stays 200', async ({ page }) => {
  const csrf = await loginAndCsrf(page)
  await publishArticle(page, csrf, 'ARCHIVE-EMPTY-SETUP', 'archive-empty-setup')
  // Exact-ref runs can retain earlier fixtures in the task's isolated database.
  for (;;) {
    const listed = await page.request.get('/api/v1/admin/articles?limit=100&offset=0')
    expect(listed.ok()).toBeTruthy()
    const articles = await listed.json() as { id: number }[]
    if (!articles.length) break
    for (const article of articles) {
      const trashed = await page.request.delete(`/api/v1/admin/articles/${article.id}`, {
        headers: { 'X-CSRF-Token': csrf },
      })
      expect(trashed.status()).toBe(204)
    }
  }
  const response = await page.goto('/archive', { waitUntil: 'domcontentloaded' })
  expect(response?.status()).toBe(200)
  await expectHydrated(page)
  await expect(page.getByText('暂时还没有可归档的已发布文章。')).toBeVisible()
})

test('archive uses year spine, MM.DD, and 未分类', async ({ page }, testInfo) => {
  test.setTimeout(180_000)
  const csrf = await loginAndCsrf(page)
  const category = await createCategory(page, csrf, '工程实践', 'engineering-archive')
  await publishArticle(page, csrf, 'PENPOT-ARCHIVE-UNCATEGORIZED', 'penpot-archive-uncategorized')
  await publishArticle(page, csrf, 'PENPOT-ARCHIVE-CATEGORIZED', 'penpot-archive-categorized', {
    category_id: category.id,
  })
  await publishArticle(page, csrf, '从日志到索引：一次慢查询排查与复盘', 'archive-timeline-review')

  const list = await page.request.get('/api/v1/articles?limit=20&offset=0')
  expect(list.ok()).toBeTruthy()
  const articles = await list.json() as PublicArticle[]
  const uncategorized = articles.find(article => article.title === 'PENPOT-ARCHIVE-UNCATEGORIZED')
  const categorized = articles.find(article => article.title === 'PENPOT-ARCHIVE-CATEGORIZED')
  expect(uncategorized).toBeTruthy()
  expect(categorized).toBeTruthy()
  const groups = groupArticlesByYear(articles)

  await page.goto('/archive', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  const body = await page.locator('body').innerText()
  expect(body).not.toContain('48 NOTES')
  expect(body).not.toContain('2021 — 2026')
  expect(body).not.toContain(' entries')
  expect(body).not.toContain('SYSTEMS')
  await expect(page.getByRole('heading', { level: 1, name: '按时间查看文章' })).toBeVisible()
  for (const group of groups) {
    await expect(page.getByRole('heading', { level: 2, name: String(group.year) })).toBeVisible()
    await expect(page.getByText(`${group.articles.length} 篇`).first()).toBeVisible()
  }
  await expect(page.getByRole('link', { name: /PENPOT-ARCHIVE-UNCATEGORIZED/ })).toContainText('未分类')
  await expect(page.getByRole('link', { name: /PENPOT-ARCHIVE-CATEGORIZED/ })).toContainText('工程实践')
  await expect(page.getByText(archiveDayStamp(uncategorized!.published_at)).first()).toBeVisible()
  await expect(page.getByRole('link', { name: '写作台', exact: true })).toBeVisible()

  const row = page.locator('.archive-row').first()
  await row.focus()
  expect(await row.evaluate(element => getComputedStyle(element).outlineStyle)).toBe('solid')
  const destinations = await page.locator('.archive-row').evaluateAll(rows => rows.map(row => row.getAttribute('href')))
  expect(destinations).toEqual(articles.map(article => article.public_path))
  await page.setViewportSize({ width: 1280, height: 900 })
  for (const theme of ['light', 'dark']) {
    await page.evaluate(theme => {
      document.documentElement.classList.toggle('dark', theme === 'dark')
      document.documentElement.classList.toggle('light', theme === 'light')
    }, theme)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await page.locator('.archive-spine').screenshot({ path: join(testInfo.project.outputDir, `archive-${theme}.png`) })
  }

  await page.setViewportSize({ width: 390, height: 844 })
  const mobile = await page.locator('.archive-row').first().evaluate(element => ({
    display: getComputedStyle(element).display,
    direction: getComputedStyle(element).flexDirection,
  }))
  expect(mobile.display).toBe('grid')
  const date = await page.locator('.archive-row-date').first().boundingBox()
  const title = await page.locator('.archive-row-title').first().boundingBox()
  expect(date!.x).toBeLessThan(title!.x)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.locator('.archive-spine').screenshot({ path: join(testInfo.project.outputDir, 'archive-mobile.png') })
  await page.setViewportSize({ width: 1440, height: 900 })
  const desktop = await page.locator('.archive-row').first().evaluate(element => getComputedStyle(element).display)
  expect(desktop).toBe('grid')
  await page.setViewportSize({ width: 1024, height: 800 })
  await expect(page.getByRole('button', { name: '打开主导航菜单' })).toBeVisible()
})
