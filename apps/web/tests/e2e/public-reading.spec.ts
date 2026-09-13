import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { join } from 'node:path'
import { expectHydrated } from '../support/hydration'

const login = async (page: Page) => {
  await page.goto('/admin/login')
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  return { 'X-CSRF-Token': (await page.context().cookies()).find(c => c.name === 'gavin_csrf')!.value }
}

const publish = async (page: Page, headers: Record<string, string>, type: string, data: Record<string, unknown>) => {
  const created = await page.request.post(`/api/v1/admin/${type}`, { headers, data })
  expect(created.status(), await created.text()).toBe(201)
  const draft = await created.json()
  const response = await page.request.post(`/api/v1/admin/${type}/${draft.id}/publish`, { headers, data: { version: draft.version } })
  expect(response.ok(), await response.text()).toBe(true)
  return response.json()
}

const body = [
  '# 问题与边界', '审查样例：验证已发布内容的阅读与导航，不代表个人项目成果。',
  ['```bash', 'echo public-reading', '```'].join('\n'),
  '## 验证过程', ['```typescript', 'const published = true', `const longLine = "${'abcdefgh'.repeat(32)}"`, '```'].join('\n'),
  ['| 证据 | 输入 | 输出 | 说明 | 约束 |', '| --- | --- | --- | --- | --- |',
    `| 实测 | ${'unbroken'.repeat(18)} | 正常 | 局部滚动 | 不扩张页面 |`].join('\n'),
  '> 阅读摘录，出处见下方。\n>\n> —— 审查样例，第 12 页',
  '## 结论与来源', '保留原文和可核对的依据。[^source]', '[^source]: 这里是已发布正文的脚注。',
].join('\n\n')

const noOverflow = async (page: Page, label: string) => {
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth), label).toBeLessThanOrEqual(1)
}

test('phase three reading keeps one responsive TOC and compact copyable code', async ({ page }) => {
  const navigationWarnings: string[] = []
  page.on('console', message => { if (message.text().includes('VUE_ROUTER_R0042')) navigationWarnings.push(message.text()) })
  const headers = await login(page)
  const article = await publish(page, headers, 'articles', { title: '审查样例：阅读轴与目录', slug: 'phase3-reading', content: body })
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto(article.public_path)
  await expectHydrated(page)
  await expect(page.getByRole('heading', { level: 1 })).toHaveCount(1)
  await expect(page.getByRole('navigation', { name: '文章目录' })).toHaveCount(1)
  const title = await page.locator('h1').boundingBox()
  const prose = await page.locator('.reading-body').boundingBox()
  expect(prose!.width).toBe(740)
  expect(title!.x).toBe(prose!.x)
  await expect(page.locator('.article-hero-meta time')).toBeVisible()
  const single = page.locator('.article-code[data-lines="single"]')
  expect((await single.boundingBox())!.height).toBeLessThan(110)
  await page.context().grantPermissions(['clipboard-read', 'clipboard-write'])
  await single.getByRole('button', { name: '复制', exact: true }).click()
  expect((await page.evaluate(() => navigator.clipboard.readText())).replace(/\r\n/g, '\n')).toBe('echo public-reading\n')
  await page.setViewportSize({ width: 390, height: 480 })
  const toc = page.locator('.reading-toc details')
  await expect(toc).toBeVisible()
  expect((await toc.boundingBox())!.y).toBeLessThan((await page.locator('.reading-body').boundingBox())!.y)
  await toc.locator('summary').focus()
  await page.keyboard.press('Enter')
  await toc.getByRole('link', { name: '结论与来源' }).click()
  await expect(toc).not.toHaveAttribute('open')
  await expect(page.getByRole('heading', { name: '结论与来源' })).toBeFocused()
  await page.locator('.footnote-ref a').click()
  await expect(page.locator('.footnotes')).toBeVisible()
  await noOverflow(page, 'mobile reading')
  expect(navigationWarnings).toEqual([])
  await expect(page.locator('[data-table-scroll]')).toHaveAttribute('tabindex', '0')
  expect(await page.locator('[data-table-scroll]').evaluate(el => el.scrollWidth > el.clientWidth)).toBe(true)
})

test('phase three project and book navigation preserves published snapshots and metadata', async ({ page }) => {
  const headers = await login(page)
  const article = await publish(page, headers, 'articles', { title: 'PhaseThreeSource 审查来源', slug: 'phase3-source', content: '# 依据\n\n真实发布样例。' })
  const diagram = '\n\n```mermaid\nflowchart LR\n  Input[输入] --> Check[校验]\n  Check --> Output[输出]\n```'
  const project = await publish(page, headers, 'projects', { title: 'PhaseThreeProject 审查样例：发布与阅读', slug: 'phase3-project', content: body + diagram, summary: '隔离审查样例：从输入到校验，再读取已发布结果。', article_ids: [article.id] })
  const book = await publish(page, headers, 'books', { book_title: 'PhaseThreeBook 审查样例：没有封面的阅读笔记', author: '审查作者', slug: 'phase3-book', content: body, cover_url: null, reading_status: 'completed', rating: 4 })
  for (const [type, item, name] of [['projects', project, project.title], ['books', book, book.book_title]] as const) {
    const working = await page.request.get(`/api/v1/admin/${type}/${item.id}`)
    const current = await working.json()
    const patch = await page.request.patch(`/api/v1/admin/${type}/${item.id}`, { headers, data: { version: current.version, content: 'UNPUBLISHED_PHASE_THREE_PRIVATE' } })
    expect(patch.ok()).toBe(true)
    await page.goto(`/${type}`)
    await expectHydrated(page)
    await page.getByRole('link').filter({ hasText: name }).first().click()
    await expect(page).toHaveURL(new RegExp(`${item.public_path}$`))
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(name)
    await expect(page.locator('body')).not.toContainText('UNPUBLISHED_PHASE_THREE_PRIVATE')
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute('href', new URL(item.public_path, page.url()).href)
    const ld = await page.locator('script[type="application/ld+json"]').allTextContents()
    expect(ld.join('')).toContain(type === 'projects' ? 'CreativeWork' : 'Review')
    await page.setViewportSize({ width: 390, height: 844 })
    await expect(page.locator('.reading-toc details')).toBeVisible()
    await expect(page.locator('.book-cover-fallback')).toHaveCount(0)
    if (type === 'books') await expect(page.locator('.book-real-cover')).toHaveCount(0)
    else {
      await expect(page.locator('[data-mermaid-block] svg')).toBeVisible()
      await page.getByRole('link').filter({ hasText: article.title }).click()
      await expect(page).toHaveURL(new RegExp(`${article.public_path}$`))
    }
    await page.goto('/search')
    await expectHydrated(page)
    await page.getByTestId('search-input').fill(type === 'projects' ? 'PhaseThreeProject' : 'PhaseThreeBook')
    await page.getByTestId('search-submit').click()
    await page.getByTestId('search-results').getByRole('link').filter({ hasText: name }).click()
    await expect(page).toHaveURL(new RegExp(`${item.public_path}$`))
    await expect(page.locator('body')).not.toContainText('UNPUBLISHED_PHASE_THREE_PRIVATE')
  }
})

test('phase three public surfaces fit long content in both themes and short viewports', async ({ page }, testInfo) => {
  const headers = await login(page)
  const title = `审查长标题：${'EngineeringWithoutSpaces'.repeat(5)}`
  const article = await publish(page, headers, 'articles', { title, slug: 'phase3-visual-article', content: body })
  const project = await publish(page, headers, 'projects', { title, slug: 'phase3-visual-project', content: body, summary: '项目审查样例，正文没有结构图。', article_ids: [] })
  const book = await publish(page, headers, 'books', { book_title: title, author: '审查作者', slug: 'phase3-visual-book', content: body, reading_status: 'reading', cover_url: new URL('/og/gavin-notes-default.png', page.url()).href })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  const routes = ['/articles', '/projects', '/books', '/archive', '/about', '/search?q=EngineeringWithoutSpaces', article.public_path, project.public_path, book.public_path, '/phase3-missing']
  for (const [index, path] of routes.entries()) {
    const response = await page.goto(path)
    if (path === '/phase3-missing') {
      expect(response?.status()).toBe(404)
      await expect(page.locator('.public-error')).toBeVisible()
    }
    else await expectHydrated(page)
    for (const theme of ['light', 'dark']) {
      await page.evaluate(value => { document.documentElement.classList.toggle('dark', value === 'dark') }, theme)
      for (const width of [320, 390, 639, 640, 768, 1024, 1100, 1101, 1280, 1440]) {
        await page.setViewportSize({ width, height: 480 })
        await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => resolve())))
        await noOverflow(page, `${path} ${theme} ${width}`)
        if (path === '/about') {
          const position = await page.evaluate(() => {
            const name = document.querySelector('h1')!.getBoundingClientRect()
            const bio = document.querySelector('.about-page-intro')!.getBoundingClientRect()
            return { nameX: name.x, bioX: bio.x, nameBottom: name.bottom, bioY: bio.y }
          })
          expect(position.bioX - position.nameX, `${theme} ${width} introduction alignment`).toBeCloseTo(0, 0)
          expect(position.nameBottom, `${theme} ${width}`).toBeLessThan(position.bioY)
        }
      }
      const axe = new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      // Nuxt dev adds an error inspector with nested controls; production scans the entire error document.
      if (path === '/phase3-missing') axe.include('.public-error')
      expect((await axe.analyze()).violations).toEqual([])
      for (const width of [390, 1440]) {
        await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 })
        await page.screenshot({ path: join(testInfo.project.outputDir, `pr-${index}-${theme}-${width}.png`), fullPage: true })
      }
    }
    if (path === project.public_path) await expect(page.locator('[data-mermaid-block]')).toHaveCount(0)
    if (path === book.public_path) await expect(page.locator('.book-real-cover')).toBeVisible()
  }
})

test('phase three list loading and empty states remain distinct', async ({ page }) => {
  await page.goto('/about')
  await expectHydrated(page)
  for (const type of ['projects', 'books', 'articles']) {
    await page.route(`**/api/v1/${type}?*`, route => route.fulfill({ json: [] }))
    await page.getByRole('navigation', { name: '主导航', exact: true }).getByRole('link', { name: type === 'projects' ? '项目' : type === 'books' ? '读书' : '文章', exact: true }).click()
    await expect(page.locator('.empty-state')).toBeVisible()
    await expect(page.locator('.public-loading')).toHaveCount(0)
    await page.unroute(`**/api/v1/${type}?*`)
  }
  let release!: () => void
  const wait = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/v1/articles?*', async route => { await wait; await route.fulfill({ json: [] }) })
  await page.evaluate(() => { void window.history.pushState({}, '', '/articles?page=2'); window.dispatchEvent(new PopStateEvent('popstate')) })
  await expect(page.locator('.public-loading')).toHaveText('正在读取内容…')
  await expect(page.getByTestId('articles-results')).toHaveAttribute('aria-busy', 'true')
  await expect(page.getByTestId('articles-empty')).toHaveCount(0)
  release()
  await expect(page.getByTestId('articles-empty')).toBeVisible()
})
