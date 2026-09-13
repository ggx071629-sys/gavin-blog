import { expect, test } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

// Same 1x1 PNG fixture the profile media flow already uploads through the real pipeline.
const PNG_BYTES = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
  'base64',
)

test('book cover chosen from the media library saves, persists, and renders for a visitor', async ({ page, browser }) => {
  test.setTimeout(120_000)
  await page.goto('/admin/login', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)

  const csrf = (await page.context().cookies()).find(cookie => cookie.name === 'gavin_csrf')?.value
  expect(csrf).toBeTruthy()
  const headers = { 'X-CSRF-Token': csrf! }

  const uploaded = await page.request.post('/api/v1/admin/media', {
    headers,
    multipart: {
      file: { name: 'cover.png', mimeType: 'image/png', buffer: PNG_BYTES },
      alt_text: '封面样例',
    },
  })
  expect(uploaded.status()).toBe(201)
  const asset = await uploaded.json() as { url: string }
  expect(asset.url).toMatch(/^\/api\/v1\/media\/[1-9][0-9]*\/webp$/)

  const created = await page.request.post('/api/v1/admin/books', {
    headers,
    data: {
      book_title: '封面契约之书',
      author: '审查作者',
      slug: `cover-contract-${Date.now()}`,
      content: '# 封面契约\n\n正文。',
    },
  })
  expect(created.status()).toBe(201)
  const book = await created.json() as { id: number, slug: string }

  await page.goto(`/admin/books/${book.id}/edit`, { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  const coverInput = page.getByTestId('book-cover-url')

  await coverInput.fill('/etc/passwd')
  await expect(page.locator('.writing-validation')).toHaveText('请填写 http(s):// 图片地址，或从媒体库选择站内封面。')

  const coverSection = page.getByRole('region', { name: '书籍封面' })
  await coverSection.getByTestId('toggle-media-library').click()
  const assetCard = page.locator('.admin-media-asset').filter({ has: page.locator(`img[src$="${asset.url}"]`) })
  await assetCard.getByRole('button', { name: '使用 URL' }).click()
  await expect(coverInput).toHaveValue(asset.url)
  await expect(page.locator('.save-state')).toHaveText('已自动保存')

  await page.reload({ waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await expect(page.getByTestId('book-cover-url')).toHaveValue(asset.url)

  await page.getByRole('button', { name: '预览', exact: true }).click()
  await expect(page.getByTestId('book-editor-preview')).toContainText('封面契约')
  await expect(page.getByTestId('book-editor-preview')).toContainText('正文。')
  await page.getByRole('button', { name: 'Markdown', exact: true }).click()

  await page.getByTestId('book-slug').fill('Invalid Slug')
  await expect(page.locator('.writing-validation')).toHaveText('Slug 只能使用小写英文字母、数字和单个连字符。')
  await page.getByTestId('book-slug').fill(book.slug)
  await expect(page.locator('.save-state')).toHaveText('已自动保存')

  await page.getByTestId('publish-book').click()
  await page.getByTestId('confirm-publish').click()
  await expect(page).toHaveURL(/\/books\/\d{4}\/\d{2}\//)
  const publicPath = new URL(page.url()).pathname

  const visitor = await browser.newContext()
  try {
    const visitorPage = await visitor.newPage()
    await visitorPage.goto(publicPath, { waitUntil: 'domcontentloaded' })
    const cover = visitorPage.locator('.book-real-cover')
    await expect(cover).toBeVisible()
    await expect(cover).toHaveAttribute('src', asset.url)
    await expect.poll(() => cover.evaluate((image: HTMLImageElement) => image.naturalWidth)).toBeGreaterThan(0)
  }
  finally {
    await visitor.close()
  }
})
