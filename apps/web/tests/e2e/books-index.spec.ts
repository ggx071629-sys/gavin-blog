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

const trashAllBooks = async (page: Page, csrf: string) => {
  const listed = await page.request.get('/api/v1/admin/books?limit=100&offset=0')
  expect(listed.ok()).toBeTruthy()
  const notes = await listed.json() as { id: number }[]
  for (const note of notes) {
    const trashed = await page.request.delete(`/api/v1/admin/books/${note.id}`, {
      headers: { 'X-CSRF-Token': csrf },
    })
    expect(trashed.status(), String(note.id)).toBe(204)
  }
}

const publishBook = async (
  page: Page,
  csrf: string,
  bookTitle: string,
  slug: string,
  extras: { reading_status?: 'planned' | 'reading' | 'completed' | 'paused'; reading_date?: string | null; summary?: string } = {},
) => {
  const created = await page.request.post('/api/v1/admin/books', {
    headers: { 'X-CSRF-Token': csrf },
    data: {
      book_title: bookTitle,
      author: 'PENPOT-BOOKS-AUTHOR',
      slug,
      cover_url: null,
      reading_status: extras.reading_status ?? 'completed',
      reading_date: extras.reading_date ?? '2026-08-08',
      rating: null,
      summary: extras.summary ?? `${bookTitle} summary`,
      content: `# ${bookTitle}\n\nnote`,
    },
  })
  expect(created.status(), bookTitle).toBe(201)
  const note = await created.json()
  const published = await page.request.post(`/api/v1/admin/books/${note.id}/publish`, {
    headers: { 'X-CSRF-Token': csrf },
    data: { version: note.version },
  })
  expect(published.ok(), bookTitle).toBeTruthy()
  return note
}

const expectNoPageOverflow = async (page: Page, label: string) => {
  const width = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }))
  expect(width.scroll, label).toBeLessThanOrEqual(width.client)
}

test('empty books index stays 200 without a reading highlight', async ({ page }) => {
  const csrf = await loginAndCsrf(page)
  await trashAllBooks(page, csrf)
  await page.goto('/books', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await expect(page.getByText('暂时还没有已发布读书笔记。')).toBeVisible()
  await expect(page.getByTestId('books-current')).toHaveCount(0)
})

test('books index uses a page-local reading highlight and ledger rows', async ({ page }) => {
  test.setTimeout(180_000)
  const csrf = await loginAndCsrf(page)
  await trashAllBooks(page, csrf)
  await publishBook(page, csrf, 'PENPOT-BOOKS-DONE-A', 'penpot-books-done-a', { reading_status: 'completed' })
  await publishBook(page, csrf, 'PENPOT-BOOKS-READING', 'penpot-books-reading', {
    reading_status: 'reading',
    summary: 'PENPOT-BOOKS-READING-NOTE',
  })

  await page.goto('/books', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  const body = await page.locator('body').innerText()
  expect(body).not.toContain('PAGE 416')
  expect(body).not.toContain('APPLIED')
  expect(body).not.toContain('12 BOOKS')
  expect(body).not.toContain('当前阅读')
  expect(body.toLowerCase()).not.toContain('currently reading')
  await expect(page.getByTestId('books-current')).toContainText('在读')
  await expect(page.getByTestId('books-current')).toContainText('PENPOT-BOOKS-READING')
  await expect(page.getByTestId('books-current')).toContainText('PENPOT-BOOKS-READING-NOTE')
  await expect(page.getByTestId('book-card').filter({ hasText: 'PENPOT-BOOKS-READING' })).toBeVisible()
  await expect(page.getByTestId('book-card').filter({ hasText: 'PENPOT-BOOKS-DONE-A' })).toBeVisible()
  await expect(page.getByText('2026.08').first()).toBeVisible()
  await expect(page.getByRole('link', { name: '写作台', exact: true })).toBeVisible()

  await page.setViewportSize({ width: 390, height: 844 })
  await expectNoPageOverflow(page, 'books 390')
  const mobileRow = await page.locator('.book-ledger-link').first().evaluate(element => getComputedStyle(element).flexDirection)
  expect(mobileRow).toBe('column')

  await page.setViewportSize({ width: 1440, height: 900 })
  await expectNoPageOverflow(page, 'books 1440')
  const desktopRow = await page.locator('.book-ledger-link').first().evaluate(element => getComputedStyle(element).flexDirection)
  expect(desktopRow).toBe('column')
  const cards = page.getByTestId('book-card')
  const first = await cards.nth(0).boundingBox()
  const second = await cards.nth(1).boundingBox()
  expect(Math.abs(first!.y - second!.y)).toBeLessThan(2)
  expect(second!.x).toBeGreaterThan(first!.x + first!.width)

  await page.setViewportSize({ width: 1024, height: 800 })
  await expect(page.getByRole('button', { name: '打开主导航菜单' })).toBeVisible()
})

test('reading highlight hides on pages without a reading book', async ({ page }) => {
  test.setTimeout(180_000)
  const csrf = await loginAndCsrf(page)
  await trashAllBooks(page, csrf)
  for (let index = 0; index < 12; index += 1) {
    await publishBook(page, csrf, `PENPOT-BOOKS-DONE-${index + 1}`, `penpot-books-done-${index + 1}`, {
      reading_status: 'completed',
    })
  }
  await publishBook(page, csrf, 'PENPOT-BOOKS-READING', 'penpot-books-reading-page', { reading_status: 'reading' })

  await page.goto('/books', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await expect(page.getByTestId('books-current')).toContainText('PENPOT-BOOKS-READING')

  await page.getByTestId('pagination-next').click()
  await expect(page).toHaveURL(/page=2/)
  await expectHydrated(page)
  await expect(page.getByText('PENPOT-BOOKS-DONE-1', { exact: true })).toBeVisible()
  await expect(page.getByTestId('books-current')).toHaveCount(0)
  const pageTwo = await page.locator('body').innerText()
  expect(pageTwo).not.toContain('当前阅读')
  expect(pageTwo).not.toContain('PENPOT-BOOKS-READING')
})

test('books pending keeps prior rows', async ({ page }) => {
  test.setTimeout(180_000)
  const csrf = await loginAndCsrf(page)
  await trashAllBooks(page, csrf)
  for (let index = 0; index < 13; index += 1) {
    await publishBook(page, csrf, `PENPOT-BOOKS-PAGE-${index + 1}`, `penpot-books-page-${index + 1}`)
  }

  await page.goto('/books', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await page.route('**/api/v1/books**', async (route) => {
    const url = new URL(route.request().url())
    if (url.searchParams.get('offset') === '12') {
      await new Promise(resolve => setTimeout(resolve, 2000))
    }
    await route.continue()
  })
  await page.getByTestId('pagination-next').click()
  await expect(page.getByTestId('books-results')).toHaveAttribute('aria-busy', 'true')
  await expect(page.getByTestId('book-card').first()).toBeVisible()
})
