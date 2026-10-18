import { expect, test, type Page } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

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

const createTag = async (page: Page, csrf: string, name: string, slug: string) => {
  const created = await page.request.post('/api/v1/admin/tags', {
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
  extras: { category_id?: number; tag_ids?: number[] } = {},
) => {
  const created = await page.request.post('/api/v1/admin/articles', {
    headers: { 'X-CSRF-Token': csrf },
    data: {
      title,
      slug,
      summary: `${title} summary`,
      content: `# ${title}\n\n${'word '.repeat(80)}`,
      category_id: extras.category_id ?? null,
      tag_ids: extras.tag_ids ?? [],
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

test('articles index uses real categories, URL rules, and a row list', async ({ page }) => {
  test.setTimeout(180_000)
  const csrf = await loginAndCsrf(page)
  const engineering = await createCategory(page, csrf, '工程实践列表', 'engineering-list')
  const notes = await createCategory(page, csrf, '现场笔记', 'field-notes')
  const tag = await createTag(page, csrf, '检索', 'retrieval')
  await publishArticle(page, csrf, 'PENPOT-ARTICLES-TAG', 'penpot-articles-tag', {
    category_id: notes.id,
    tag_ids: [tag.id],
  })
  for (let index = 0; index < 12; index += 1) {
    await publishArticle(page, csrf, `PENPOT-ARTICLES-PAGE ${index + 1}`, `penpot-articles-page-${index + 1}`, {
      category_id: engineering.id,
    })
  }
  await publishArticle(page, csrf, 'PENPOT-ARTICLES-ENG', 'penpot-articles-eng', {
    category_id: engineering.id,
  })

  await page.goto('/articles', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  const body = await page.locator('body').innerText()
  expect(body).not.toContain('SYSTEMS')
  expect(body).not.toContain('DESIGN')
  expect(body).not.toContain('TOOLS')
  await expect(page.getByTestId('articles-category-strip')).toContainText('工程实践')
  await expect(page.getByTestId('articles-category-strip')).toContainText('全部')
  await expect(page.getByRole('link', { name: '搜索全部内容' })).toBeVisible()
  await expect(page.getByRole('link', { name: '写作台', exact: true })).toBeVisible()
  await expect(page.locator('.article-list-row').first()).toBeVisible()

  await page.getByRole('link', { name: /工程实践列表/ }).first().click()
  await expect(page).toHaveURL(/\/articles\?category=engineering-list$/)
  await expect(page.getByRole('heading', { name: 'PENPOT-ARTICLES-ENG' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'PENPOT-ARTICLES-TAG' })).toHaveCount(0)

  await page.getByTestId('pagination-next').click()
  await expect(page).toHaveURL(/category=engineering/)
  await expect(page).toHaveURL(/page=2/)

  await page.getByRole('link', { name: /^全部 / }).click()
  await expect(page).toHaveURL(/\/articles$/)

  await page.locator('.articles-tag-row').getByRole('link', { name: '检索', exact: true }).click()
  await expect(page).toHaveURL(/\/articles\?tag=retrieval$/)
  await expect(page.getByRole('heading', { name: 'PENPOT-ARTICLES-TAG' })).toBeVisible()

  await page.goto('/articles?category=engineering-list&tag=retrieval', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await expect(page.locator('.articles-filter-link[data-active="true"]')).toHaveCount(1)
  await expect(page.locator('.filter-chip[data-active="true"]')).toHaveCount(1)

  await page.setViewportSize({ width: 1024, height: 800 })
  await page.goto('/articles', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await expect(page.getByRole('button', { name: '打开主导航菜单' })).toBeVisible()
  const row = await page.locator('.article-list-row').first().evaluate(element => getComputedStyle(element).flexDirection)
  expect(row).toBe('row')
})

test('390 filters wrap within the viewport and article rows stack', async ({ page }) => {
  test.setTimeout(180_000)
  const csrf = await loginAndCsrf(page)
  for (let index = 0; index < 8; index += 1) {
    const category = await createCategory(page, csrf, `长栏目名称筛选条 ${index + 1}`, `long-cat-${index + 1}`)
    await publishArticle(page, csrf, `PENPOT-ARTICLES-LONG ${index + 1}`, `penpot-articles-long-${index + 1}`, {
      category_id: category.id,
    })
  }
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/articles', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  const strip = page.getByTestId('articles-category-strip')
  const metrics = await strip.evaluate((element) => {
    const style = getComputedStyle(element)
    return {
      overflowX: style.overflowX,
      client: element.clientWidth,
      scroll: element.scrollWidth,
      wrap: style.flexWrap,
    }
  })
  expect(metrics.wrap).toBe('wrap')
  expect(metrics.scroll).toBeLessThanOrEqual(metrics.client)
  await expect(strip.getByRole('link', { name: /长栏目名称筛选条/ })).toHaveCount(8)
  expect(await page.locator('.article-list-row').first().evaluate(element => getComputedStyle(element).flexDirection)).toBe('column')
  const pageWidth = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }))
  expect(pageWidth.scroll).toBeLessThanOrEqual(pageWidth.client)
  await expect(page.getByRole('button', { name: '打开主导航菜单' })).toBeVisible()
})

test('pending keeps prior rows and a slower request cannot replace a later one', async ({ page }) => {
  test.setTimeout(180_000)
  const csrf = await loginAndCsrf(page)
  const fast = await createCategory(page, csrf, '快栏目', 'fast-cat')
  const slow = await createCategory(page, csrf, '慢栏目', 'slow-cat')
  await publishArticle(page, csrf, 'PENPOT-ARTICLES-FAST', 'penpot-articles-fast', { category_id: fast.id })
  await publishArticle(page, csrf, 'PENPOT-ARTICLES-SLOW', 'penpot-articles-slow', { category_id: slow.id })

  await page.goto('/articles', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await expect(page.getByRole('heading', { name: 'PENPOT-ARTICLES-FAST' })).toBeVisible()

  await page.route('**/api/v1/articles**', async (route) => {
    const url = new URL(route.request().url())
    if (url.searchParams.get('category') === 'slow-cat') {
      await new Promise(resolve => setTimeout(resolve, 2000))
    }
    await route.continue()
  })

  await page.getByRole('link', { name: /慢栏目/ }).first().click()
  await expect(page.getByTestId('articles-results')).toHaveAttribute('aria-busy', 'true')
  await expect(page.getByRole('heading', { name: 'PENPOT-ARTICLES-FAST' })).toBeVisible()
  await expect(page.getByTestId('articles-empty')).toHaveCount(0)

  await page.getByRole('link', { name: /快栏目/ }).first().click()
  await expect(page.getByRole('heading', { name: 'PENPOT-ARTICLES-FAST' })).toBeVisible({ timeout: 10_000 })
  await expect(page.getByRole('heading', { name: 'PENPOT-ARTICLES-SLOW' })).toHaveCount(0)
})

test('home cards and books hero do not pick up the articles list contract', async ({ page }) => {
  test.setTimeout(180_000)
  const csrf = await loginAndCsrf(page)
  await publishArticle(page, csrf, 'PENPOT-ARTICLES-HOME', 'penpot-articles-home')
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await expect(page.getByTestId('home-featured')).toBeVisible()
  await expect(page.getByTestId('home-featured')).toContainText('PENPOT-ARTICLES-HOME')
  await expect(page.locator('.article-list-row')).toHaveCount(0)
  await page.goto('/books', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await expect(page.getByRole('heading', { level: 1, name: '读过的书与读书笔记' })).toBeVisible()
})
