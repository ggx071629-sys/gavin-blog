import { expect, test } from '@playwright/test'
import { expectHydrated as waitForHydration } from '../support/hydration'

test('published content exposes canonical metadata and discovery documents', async ({ page, request }) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  const websiteJsonLd = JSON.parse(await page.locator('script[type="application/ld+json"]').textContent() || '{}')
  expect(websiteJsonLd.potentialAction).toEqual({
    '@type': 'SearchAction',
    target: `${new URL(page.url()).origin}/search?q={search_term_string}`,
    'query-input': 'required name=search_term_string',
  })

  await page.goto('/admin/login', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)

  const csrf = (await page.context().cookies()).find(cookie => cookie.name === 'gavin_csrf')?.value
  expect(csrf).toBeTruthy()
  const headers = { 'X-CSRF-Token': csrf! }
  const categoryResponse = await page.request.post('/api/v1/admin/categories', {
    headers,
    data: { name: 'SEO 工程', slug: 'seo-engineering' },
  })
  expect(categoryResponse.status()).toBe(201)
  const category = await categoryResponse.json()
  const tagResponse = await page.request.post('/api/v1/admin/tags', {
    headers,
    data: { name: 'Discovery', slug: 'discovery' },
  })
  expect(tagResponse.status()).toBe(201)
  const tag = await tagResponse.json()

  const publishArticle = async (title: string, slug: string, content: string) => {
    const createdResponse = await page.request.post('/api/v1/admin/articles', {
      headers,
      data: {
        title,
        slug,
        summary: '',
        content,
        category_id: category.id,
        tag_ids: [tag.id],
      },
    })
    expect(createdResponse.status()).toBe(201)
    const created = await createdResponse.json()
    const publishedResponse = await page.request.post(`/api/v1/admin/articles/${created.id}/publish`, {
      headers,
      data: { version: created.version },
    })
    expect(publishedResponse.ok()).toBe(true)
    return publishedResponse.json()
  }

  await publishArticle('更早的 SEO 笔记', 'older-discovery-note', '# 更早\n\n公开上下文。')
  const target = await publishArticle(
    '可发现的技术笔记',
    'discoverable-note',
    '# 可发现\n\n这是一篇使用 **Responses API** 验证 SEO 输出的文章，并附有[阅读文档](https://example.com)。\n\n## 深入验证',
  )
  await publishArticle('更新的 SEO 笔记', 'newer-discovery-note', '# 更新\n\n公开上下文。')

  const revisedResponse = await page.request.patch(`/api/v1/admin/articles/${target.id}`, {
    headers,
    data: {
      content: '# 可发现\n\n这是一篇使用 **Responses API** 验证 SEO 输出的文章，并附有[阅读文档](https://example.com)。\n\n## 深入验证\n\n修订后的公开内容。',
      version: target.version,
    },
  })
  expect(revisedResponse.ok()).toBe(true)
  const revised = await revisedResponse.json()
  const republishedResponse = await page.request.post(`/api/v1/admin/articles/${target.id}/publish`, {
    headers,
    data: { version: revised.version },
  })
  expect(republishedResponse.ok()).toBe(true)
  const republished = await republishedResponse.json()

  const unusedEnhancerRequests: string[] = []
  page.on('request', (request) => {
    if (/mermaid|katex|markdown-it-texmath/i.test(request.url())) {
      unusedEnhancerRequests.push(request.url())
    }
  })
  await page.goto(republished.public_path, { waitUntil: 'networkidle' })
  await expect(page).toHaveURL(/\/notes\/\d{4}\/\d{2}\/discoverable-note$/)
  expect(unusedEnhancerRequests, 'plain article enhancer requests').toEqual([])

  const siteOrigin = new URL(page.url()).origin
  const canonical = page.locator('link[rel="canonical"]')
  const canonicalHref = await canonical.getAttribute('href')
  expect(canonicalHref).not.toBeNull()
  expect(new URL(canonicalHref!).origin).toBe(siteOrigin)
  expect(new URL(canonicalHref!).pathname).toMatch(/^\/notes\/\d{4}\/\d{2}\/discoverable-note$/)
  await expect(page.locator('meta[property="og:title"]')).toHaveAttribute('content', '可发现的技术笔记')
  await expect(page.locator('meta[property="og:type"]')).toHaveAttribute('content', 'article')
  await expect(page.locator('meta[property="og:image"]')).toHaveAttribute('content', `${siteOrigin}/og/gavin-notes-default.png`)
  await expect(page.locator('meta[property="og:image:width"]')).toHaveAttribute('content', '1200')
  await expect(page.locator('meta[property="og:image:height"]')).toHaveAttribute('content', '630')
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', 'index,follow')
  const description = await page.locator('meta[name="description"]').getAttribute('content') || ''
  expect(description).toContain('Responses API')
  expect(description).not.toMatch(/[*`[\]#]/)
  await expect(page.getByRole('heading', { level: 1 })).toHaveCount(1)
  await expect(page.getByRole('heading', { level: 2, name: '可发现' })).toHaveAttribute('id', encodeURIComponent('可发现'))
  await expect(page.getByRole('heading', { level: 3, name: '深入验证' })).toBeVisible()
  await expect(page.getByTestId('article-updated-at')).toContainText('最后更新')
  await expect(page.getByTestId('article-neighbors').getByRole('link', { name: /更早的 SEO 笔记/ })).toBeVisible()
  await expect(page.getByTestId('article-neighbors').getByRole('link', { name: /更新的 SEO 笔记/ })).toBeVisible()
  await expect(page.getByTestId('related-articles').getByRole('link')).toHaveCount(2)

  const jsonLd = JSON.parse(await page.locator('script[type="application/ld+json"]').textContent() || '{}')
  expect(jsonLd['@type']).toBe('BlogPosting')
  expect(jsonLd.headline).toBe('可发现的技术笔记')
  expect(jsonLd.description).toBe(description)
  expect(jsonLd.image).toBe(`${siteOrigin}/og/gavin-notes-default.png`)
  expect(jsonLd.author.url).toBe(`${siteOrigin}/about`)
  expect(jsonLd.publisher.url).toBe(`${siteOrigin}/`)
  expect(jsonLd.mainEntityOfPage).toBe(canonicalHref)

  const search = await request.get('/api/v1/search?q=Responses')
  expect(search.ok()).toBe(true)
  const searchResult = (await search.json()).find((result: { title: string }) => result.title === '可发现的技术笔记')
  expect(searchResult).toBeTruthy()
  expect(searchResult.snippet).toContain('Responses API')
  expect(searchResult.snippet).not.toMatch(/[*`[\]#]/)

  const rss = await request.get('/rss.xml')
  expect(rss.ok()).toBe(true)
  expect(rss.headers()['content-type']).toContain('application/rss+xml')
  const rssText = await rss.text()
  expect(rssText).toContain('discoverable-note')
  expect(rssText).not.toContain('**Responses API**')

  const sitemap = await request.get('/sitemap.xml')
  expect(sitemap.ok()).toBe(true)
  expect(await sitemap.text()).toContain('discoverable-note')

  const robots = await request.get('/robots.txt')
  expect(robots.ok()).toBe(true)
  expect(await robots.text()).toContain('Disallow: /admin/')
  expect(await robots.text()).toContain(`Sitemap: ${siteOrigin}/sitemap.xml`)
})
