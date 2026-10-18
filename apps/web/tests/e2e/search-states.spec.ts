import { expect, test, type Page } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

const HIT = 'PENPOT-SEARCH-HIT'
const FAST = 'PENPOTSEARCHFAST'
const SLOW = 'PENPOTSEARCHSLOW'
const PAGE_TOKEN = 'PENPOTSEARCHPAGE'
const MISS = 'PENPOT-SEARCH-MISS-ZZZZ-NOHIT'

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

const publishArticle = async (page: Page, csrf: string, title: string, slug: string) => {
  const created = await page.request.post('/api/v1/admin/articles', {
    headers: { 'X-CSRF-Token': csrf },
    data: {
      title,
      slug,
      summary: `${title} summary`,
      content: `# ${title}\n\nDeterministic search seed.`,
    },
  })
  expect(created.status(), title).toBe(201)
  const article = await created.json()
  const published = await page.request.post(`/api/v1/admin/articles/${article.id}/publish`, {
    headers: { 'X-CSRF-Token': csrf },
    data: { version: article.version },
  })
  expect(published.ok(), title).toBeTruthy()
}

test('idle does not call search, empty copy differs, hits and pagination keep q', async ({ page }) => {
  test.setTimeout(180_000)
  const csrf = await loginAndCsrf(page)
  await publishArticle(page, csrf, HIT, 'penpot-search-hit')
  for (let index = 0; index < 21; index += 1) {
    await publishArticle(page, csrf, `${PAGE_TOKEN} ${String(index + 1).padStart(2, '0')}`, `penpot-search-page-${index + 1}`)
  }

  const searchRequests: string[] = []
  page.on('request', (request) => {
    if (request.url().includes('/api/v1/search')) searchRequests.push(request.url())
  })

  await page.goto('/search', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await expect(page.getByTestId('search-idle')).toBeVisible()
  expect(searchRequests.filter(url => /\/api\/v1\/search\?/.test(url))).toEqual([])

  await page.getByTestId('search-input').fill(MISS)
  await page.getByTestId('search-input').press('Enter')
  await expect(page).toHaveURL(new RegExp(`/search\\?q=${MISS}$`))
  await expect(page.getByTestId('search-empty')).toContainText('没有匹配内容')
  await expect(page.getByTestId('search-empty')).toContainText('试试更短或更具体的关键词')
  await expect(page.getByTestId('search-idle')).toHaveCount(0)

  await page.getByTestId('search-input').fill(HIT)
  await page.getByTestId('search-submit').click()
  await expect(page.getByTestId('search-results')).toBeVisible()
  await expect(page.getByRole('heading', { name: HIT })).toBeVisible()
  await expect(page.getByTestId('search-form')).toHaveAttribute('role', 'search')
  await expect(page.getByText('搜索文章、项目和读书笔记', { exact: true })).toBeAttached()

  await page.getByTestId('search-input').fill(PAGE_TOKEN)
  await page.getByTestId('search-submit').click()
  await expect(page.getByTestId('pagination-next')).toBeVisible()
  await expect(page.getByText('第 1 页')).toHaveAttribute('aria-current', 'page')
  await page.getByTestId('pagination-next').click()
  await expect(page).toHaveURL(new RegExp(`q=${PAGE_TOKEN}`))
  await expect(page).toHaveURL(/page=2/)
  await expect(page.getByText('第 2 页')).toHaveAttribute('aria-current', 'page')
  await expect(page.getByTestId('search-results')).toBeVisible()
})

test('loading hides prior hits and only the latest generation is shown', async ({ page }) => {
  test.setTimeout(180_000)
  const csrf = await loginAndCsrf(page)
  await publishArticle(page, csrf, FAST, 'penpot-search-fast')
  await publishArticle(page, csrf, SLOW, 'penpot-search-slow')

  await page.goto('/search', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await page.getByTestId('search-input').fill(FAST)
  await page.getByTestId('search-submit').click()
  await expect(page.getByRole('heading', { name: FAST })).toBeVisible()

  await page.route('**/api/v1/search**', async (route) => {
    const url = new URL(route.request().url())
    const q = url.searchParams.get('q') || ''
    if (q.includes(SLOW)) {
      await new Promise(resolve => setTimeout(resolve, 2000))
    }
    await route.continue()
  })

  await page.getByTestId('search-input').fill(SLOW)
  await page.getByTestId('search-submit').click()
  await expect(page.getByTestId('search-loading')).toBeVisible()
  await expect(page.getByTestId('search-loading')).toHaveAttribute('aria-busy', 'true')
  await expect(page.getByRole('heading', { name: FAST })).toHaveCount(0)

  await page.getByTestId('search-input').fill(FAST)
  await page.getByTestId('search-submit').click()
  await expect(page.getByRole('heading', { name: FAST })).toBeVisible({ timeout: 10_000 })
  await expect(page.getByRole('heading', { name: SLOW })).toHaveCount(0)
  await expect(page.getByTestId('search-loading')).toHaveCount(0)
})
