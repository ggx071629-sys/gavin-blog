import { expect, test } from '@playwright/test'
import { expectHydrated as waitForHydration } from '../support/hydration'

test('article reading page keeps contracts while exposing V2 chrome', async ({ page }) => {
  await page.goto('/admin/login', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  await expect(page.getByTestId('login')).toBeEnabled()
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)

  const csrf = (await page.context().cookies()).find(cookie => cookie.name === 'gavin_csrf')?.value
  expect(csrf).toBeTruthy()
  const headers = { 'X-CSRF-Token': csrf! }

  const publish = async (title: string, slug: string, content: string, extra: Record<string, unknown> = {}) => {
    const created = await page.request.post('/api/v1/admin/articles', {
      headers,
      data: { title, slug, content, ...extra },
    })
    expect(created.status()).toBe(201)
    const article = await created.json()
    const published = await page.request.post(`/api/v1/admin/articles/${article.id}/publish`, {
      headers,
      data: { version: article.version },
    })
    expect(published.ok()).toBeTruthy()
    return published.json()
  }

  const tagResponse = await page.request.post('/api/v1/admin/tags', {
    headers,
    data: { name: 'ReadingVisual', slug: 'reading-visual' },
  })
  expect(tagResponse.status()).toBe(201)
  const tag = await tagResponse.json()

  const related = await publish(
    '相关阅读单卡',
    'reading-related-note',
    '# 相关\n\n只用来占相关推荐。',
    { tag_ids: [tag.id] },
  )
  const article = await publish(
    '阅读页视觉合同',
    'reading-visual-note',
    [
      '# 阅读页视觉合同',
      '![请求链路示意](/og/gavin-notes-default.png)',
      '开篇说明复制与目录行为。',
      '## 接入 Codex',
      '先确认提供方可加载。',
      '```toml config.toml',
      'model = "deepseek-v4-flash"',
      '```',
      '## 验证结果',
      '失败时只报告剪贴板错误。',
      [
        '| Signal | Lexical | Vector | Rank | Threshold | Evidence |',
        '| --- | --- | --- | --- | --- | --- |',
        '| exact | 0.82 | 0.77 | 01 | 0.65 | retained |',
      ].join('\n'),
    ].join('\n\n'),
    { summary: '从配置到首次请求的可诊断路径。', tag_ids: [tag.id] },
  )

  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto(article.public_path, { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)

  await expect(page.getByRole('heading', { level: 1, name: '阅读页视觉合同' })).toHaveCount(1)
  await expect(page.getByTestId('article-lead-figure')).toBeVisible()
  await expect(page.getByTestId('article-start-reading')).toBeVisible()
  await expect(page.getByRole('navigation', { name: '文章目录' })).toHaveCount(1)
  await expect(page.locator('.reading-toc')).toContainText('接入 Codex')
  await expect(page.getByTestId('related-articles')).toContainText('相关文章')
  await expect(page.locator('body')).not.toContainText('adaptive')
  await expect(page.locator('body')).not.toContainText('Article signal')
  await expect(page.locator('.reading-toc .content-toc-desktop')).toBeVisible()
  await expect(page.locator('.reading-toc .content-toc-disclosure')).toBeHidden()
  await expect(page.locator('.reading-toc')).toBeVisible()
  await expect(page.getByText('TOML · CONFIG.TOML')).toBeVisible()
  await expect(page.getByRole('button', { name: '复制', exact: true })).toBeVisible()
  await expect(page.locator('.article-code-gutter')).toContainText('01')
  await expect(page.locator('.article-code-foot')).toBeHidden()
  await expect(page.getByText('VALIDATION')).toHaveCount(0)

  await page.context().grantPermissions(['clipboard-read', 'clipboard-write'])
  const codeButton = page.locator('.article-code-copy').first()
  await expect(codeButton).toHaveText('复制')
  await expect(codeButton).toHaveAttribute('data-copy-bound', 'true')
  await codeButton.focus()
  await codeButton.press('Enter')
  await expect(codeButton).toHaveText('已复制', { timeout: 1500 })
  await expect(page.locator('.article-code')).toHaveAttribute('data-copy-state', 'copied')
  expect(await page.evaluate(() => navigator.clipboard.readText())).toContain('model = "deepseek-v4-flash"')

  await page.getByTestId('article-copy-url').click()
  await expect(page.getByTestId('article-copy-url')).toHaveText('已复制链接')
  expect(await page.evaluate(() => navigator.clipboard.readText())).toContain(article.public_path)

  await page.getByTestId('article-start-reading').click()
  await expect(page.getByRole('heading', { name: '接入 Codex' })).toBeVisible()

  await page.setViewportSize({ width: 390, height: 844 })
  const tableScroll = page.locator('[data-table-scroll]')
  await expect(tableScroll).toBeVisible()
  expect(await tableScroll.evaluate((element) => element.scrollWidth > element.clientWidth)).toBeTruthy()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBeTruthy()
  await expect(page.locator('.reading-toc .content-toc-desktop')).toBeHidden()
  await expect(page.locator('.reading-toc details')).toBeVisible()
  await expect(page.locator('dialog')).toHaveCount(0)
  await page.locator('.reading-toc summary').click()
  await page.locator('.reading-toc').getByRole('link', { name: '接入 Codex' }).click()
  await expect(page.locator('.reading-toc details')).not.toHaveAttribute('open')

  await page.goto(related.public_path, { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  const relatedGrid = page.getByTestId('related-articles').locator('.article-related-grid')
  await expect(relatedGrid).toHaveAttribute('data-count', '1')
})

test('article reading variant follows the exact Short truth table and boundaries', async ({ page }) => {
  await page.goto('/admin/login', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  await expect(page.getByTestId('login')).toBeEnabled()
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)

  const csrf = (await page.context().cookies()).find(cookie => cookie.name === 'gavin_csrf')?.value
  expect(csrf).toBeTruthy()
  const headers = { 'X-CSRF-Token': csrf! }

  const publish = async (title: string, slug: string, content: string, extra: Record<string, unknown> = {}) => {
    const created = await page.request.post('/api/v1/admin/articles', {
      headers,
      data: { title, slug, content, ...extra },
    })
    expect(created.status()).toBe(201)
    const article = await created.json()
    const published = await page.request.post(`/api/v1/admin/articles/${article.id}/publish`, {
      headers,
      data: { version: article.version },
    })
    expect(published.ok()).toBeTruthy()
    return published.json()
  }

  const contentAtLength = (prefix: string, targetLength: number) => {
    expect(prefix.length).toBeLessThanOrEqual(targetLength)
    return `${prefix}${'界'.repeat(targetLength - prefix.length)}`
  }

  const categoryResponse = await page.request.post('/api/v1/admin/categories', {
    headers,
    data: { name: '短文章分类', slug: 'short-rule-category' },
  })
  expect(categoryResponse.status()).toBe(201)
  const category = await categoryResponse.json()
  const tagResponse = await page.request.post('/api/v1/admin/tags', {
    headers,
    data: { name: '边界标签', slug: 'short-rule-boundary' },
  })
  expect(tagResponse.status()).toBe(201)
  const tag = await tagResponse.json()

  const readingBoundaryContent = contentAtLength('## 唯一章节\n\n', 1000)
  const overReadingBoundaryContent = contentAtLength('## 唯一章节\n\n', 1001)
  const overHeadingBoundaryContent = contentAtLength('## 章节一\n\n正文\n\n## 章节二\n\n', 800)
  const leadFigureContent = contentAtLength('![首图](/og/gavin-notes-default.png)\n\n## 唯一章节\n\n', 800)
  expect(readingBoundaryContent).toHaveLength(1000)
  expect(overReadingBoundaryContent).toHaveLength(1001)

  const overReadingBoundary = await publish(
    '超过阅读时长边界',
    'short-rule-over-reading-boundary',
    overReadingBoundaryContent,
    {
      summary: '恰好两分钟、一个标题且没有首图。',
      category_id: category.id,
      tag_ids: [tag.id],
    },
  )
  const overHeadingBoundary = await publish(
    '超过标题数量边界',
    'short-rule-over-heading-boundary',
    overHeadingBoundaryContent,
  )
  const withLeadFigure = await publish(
    '包含首图',
    'short-rule-with-lead-figure',
    leadFigureContent,
  )
  const shortArticle = await publish(
    '短文章边界',
    'short-rule-reading-boundary',
    readingBoundaryContent,
    {
      summary: '恰好两分钟、一个标题且没有首图。',
      category_id: category.id,
      tag_ids: [tag.id],
      references: [
        {
          kind: 'internal',
          display_title: '超过阅读时长边界',
          target_type: 'article',
          target_id: overReadingBoundary.id,
        },
      ],
    },
  )

  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto(shortArticle.public_path, { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)

  const articleRoot = page.locator('.article-reading')
  await expect(articleRoot).toHaveAttribute('data-article-variant', 'short')
  await expect(articleRoot).toHaveClass(/article-reading--short/)
  await expect(page.locator('.article-hero-date')).toHaveCount(0)
  await expect(page.getByTestId('article-signal-rail')).toHaveCount(0)
  await expect(page.locator('.reading-toc')).toHaveCount(0)
  await expect(page.locator('.article-hero-meta')).toContainText('2 min read')
  await expect(page.locator('.article-hero-summary')).toHaveText('恰好两分钟、一个标题且没有首图。')
  await expect(page.locator('.article-hero-meta').getByRole('link', { name: '短文章分类' })).toBeVisible()
  await expect(page.locator('.article-hero-tags').getByRole('link', { name: '边界标签' })).toBeVisible()
  await expect(page.getByTestId('article-start-reading')).toBeVisible()
  await expect(page.getByTestId('article-copy-url')).toBeVisible()
  await expect(page.getByTestId('article-references')).toContainText('超过阅读时长边界')
  await expect(page.getByRole('link', { name: '返回文章列表', exact: true })).toBeVisible()

  const readingWidth = await page.locator('.article-reading-main').evaluate(element => element.getBoundingClientRect().width)
  expect(readingWidth).toBe(740)

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.locator('.article-hero-date')).toHaveCount(0)
  await expect(page.getByTestId('article-signal-rail')).toHaveCount(0)
  await expect(page.locator('.reading-toc')).toHaveCount(0)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBeTruthy()

  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto(overReadingBoundary.public_path, { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  await expect(articleRoot).toHaveAttribute('data-article-variant', 'long')
  await expect(articleRoot).not.toHaveClass(/article-reading--short/)
  await expect(page.locator('.article-hero-date')).toHaveCount(0)
  await expect(page.locator('.article-hero-meta time')).toBeVisible()
  await expect(page.getByTestId('article-signal-rail')).toHaveCount(0)
  await expect(page.locator('.reading-toc .content-toc-desktop')).toBeVisible()
  await expect(page.locator('.article-hero-meta')).toContainText('3 min read')
  const longHeroHeight = await page.locator('.article-hero').evaluate(element => element.getBoundingClientRect().height)
  expect(longHeroHeight).toBeLessThanOrEqual(400)
  expect(await page.locator('[data-article-body]').evaluate(element => element.getBoundingClientRect().top)).toBeLessThan(900)

  for (const candidate of [overHeadingBoundary, withLeadFigure]) {
    await page.goto(candidate.public_path, { waitUntil: 'domcontentloaded' })
    await waitForHydration(page)
    await expect(articleRoot).toHaveAttribute('data-article-variant', 'long')
    await expect(articleRoot).not.toHaveClass(/article-reading--short/)
    await expect(page.locator('.article-hero-date')).toHaveCount(0)
    await expect(page.locator('.article-hero-meta time')).toBeVisible()
    await expect(page.getByTestId('article-signal-rail')).toHaveCount(0)
    await expect(page.locator('.reading-toc .content-toc-desktop')).toBeVisible()
  }

  await expect(page.getByTestId('article-lead-figure')).toBeVisible()

  await page.goto(overHeadingBoundary.public_path, { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  await expect(page.locator('.reading-toc')).toContainText('章节一')
  await expect(page.locator('.reading-toc')).toContainText('章节二')
})
