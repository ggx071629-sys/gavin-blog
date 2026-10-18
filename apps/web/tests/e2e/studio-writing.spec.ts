import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

async function login(page: Page) {
  await page.goto('/admin/login')
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  return { 'X-CSRF-Token': (await page.context().cookies()).find(c => c.name === 'gavin_csrf')!.value }
}

test('workspace', async ({ page }, info) => {
  test.setTimeout(240_000)
  const headers = await login(page)
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  for (const [index, kind] of ['articles', 'books', 'projects'].entries()) {
    const response = await page.request.post(`/api/v1/admin/${kind}`, { headers, data: { title: '真实写作测试', book_title: '真实书名', author: '作者', slug: `workspace-${kind}-${Date.now()}`, content: '# 真实正文' } })
    expect(response.status()).toBe(201)
    const item = await response.json()
    for (const [modeIndex, suffix] of ['new', `${item.id}/edit`].entries()) {
      await page.goto(`/admin/${kind}/${suffix}`)
      await expectHydrated(page)
      const body = page.locator('.studio-markdown-field textarea')
      await body.fill('待加粗文字')
      await body.focus()
      await page.keyboard.press('ControlOrMeta+A')
      await page.getByRole('button', { name: '加粗', exact: true }).click()
      await expect(body).toHaveValue('**待加粗文字**')
      await expect(body).toBeFocused()
      await expect(page.locator('.studio-word-count')).toContainText('9 个非空白字符')
      await page.locator('.writing-mode-bar').getByRole('button', { name: '预览', exact: true }).click()
      await expect(page.locator('.writing-preview strong')).toHaveText('待加粗文字')
      await page.locator('.writing-mode-bar').getByRole('button', { name: 'Markdown', exact: true }).click()
      await expect(page.getByText('从设备插入图片', { exact: true })).toBeVisible()
      for (const dark of [false, true]) {
        await page.setViewportSize({ width: 1440, height: 1000 })
        if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== dark) await page.getByRole('button', { name: '切换颜色主题' }).filter({ visible: true }).click()
        await expect(page.locator('.admin-sidebar .admin-logout')).toHaveCSS('color', dark ? 'rgb(255, 180, 171)' : 'rgb(140, 29, 24)')
        for (const width of [1440, 1024, 768, 390, 320]) {
          await page.setViewportSize({ width, height: 900 })
          await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1)
          await expect(body).toHaveCSS('border-top-width', '0px')
          await expect(page.locator('.writing-body input[data-testid]').first()).toHaveCSS('font-size', width <= 760 ? '24px' : '28px')
          if (width === 390) {
            await expect(page.locator('.writing-settings')).toBeVisible()
            await expect(page.locator('.writing-body')).toBeVisible()
          }
          if (index === 0 && [1440, 390].includes(width)) {
            await page.evaluate(() => { (document.activeElement as HTMLElement | null)?.blur(); window.scrollTo({ top: 0, behavior: 'instant' }) })
            await expect.poll(() => page.evaluate(() => scrollY)).toBe(0)
            await page.screenshot({ path: info.outputPath(`w${modeIndex}${dark ? 'd' : 'l'}${width}.png`), fullPage: true })
          }
        }
        expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()).violations).toEqual([])
      }
      if (suffix === 'new') page.once('dialog', dialog => dialog.accept())
    }
  }
  expect(errors).toEqual([])
})
async function writingFlow(page: Page, info: import('@playwright/test').TestInfo, kind: 'articles' | 'books' | 'projects') {
  const headers = await login(page)
  const singular = kind === 'articles' ? 'article' : kind === 'books' ? 'book' : 'project'
  const titleId = kind === 'articles' ? 'new-title' : `new-${singular}-title`
  const createId = kind === 'articles' ? 'create-draft' : `create-${singular}`
  const contentId = kind === 'articles' ? 'content' : `${singular}-content`
  const publishId = kind === 'articles' ? 'publish' : `publish-${singular}`
  const slugId = kind === 'articles' ? 'slug' : `${singular}-slug`
  await page.goto(`/admin/${kind}/new`)
  await expectHydrated(page)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.getByTestId(createId).click()
  await expect(page.getByTestId(titleId)).toBeFocused()
  let draftCreates = 0
  const countCreate = (request: import('@playwright/test').Request) => { if (request.method() === 'POST' && new URL(request.url()).pathname === `/api/v1/admin/${kind}`) draftCreates++ }
  page.on('request', countCreate)
  await page.getByTestId(titleId).fill(`Studio ${kind} ${Date.now()}`)
  if (kind === 'books') {
    await page.getByTestId('new-book-author').fill('真实作者')
    await page.getByTestId('new-book-reading-status').selectOption('completed')
    await page.getByLabel('阅读日期', { exact: true }).fill('2026-09-10')
    await page.getByLabel('评分', { exact: false }).selectOption('4')
    const covers = page.locator('.writing-settings').getByTestId('toggle-media-library')
    await covers.click()
    await page.locator('.writing-settings').getByRole('button', { name: '应用筛选', exact: true }).click()
    await expect(page).toHaveURL(/\/admin\/books\/new$/)
    await covers.click()
  }
  if (kind === 'projects') {
    await page.getByLabel('仓库 URL', { exact: true }).fill('https://github.com/example/studio')
    await page.getByLabel('站点 URL', { exact: true }).fill('https://example.com/studio')
  }
  const bodyLibrary = page.locator('.writing-body').getByTestId('toggle-media-library')
  await bodyLibrary.click()
  const filtered = page.waitForResponse(response => response.request().method() === 'GET' && response.url().includes('/api/v1/admin/media?'))
  await page.locator('.writing-body').getByRole('button', { name: '应用筛选', exact: true }).click()
  await filtered
  expect(draftCreates).toBe(0)
  await expect(page).toHaveURL(new RegExp(`/admin/${kind}/new$`))
  await bodyLibrary.click()
  await page.getByTestId(createId).click()
  await expect(page).toHaveURL(new RegExp(`/admin/${kind}/\\d+/edit$`))
  expect(draftCreates).toBe(1)
  page.off('request', countCreate)
  const editPath = new URL(page.url()).pathname
  const id = Number(editPath.split('/')[3])
  await page.getByTestId(contentId).fill('# 已保存的第一版\n\n真实发布验证。')
  await page.getByTestId(publishId).click()
  await expect(page.getByRole('dialog', { name: '发布内容？' })).toBeVisible()
  const saved = await (await page.request.get(`/api/v1/admin/${kind}/${id}`)).json()
  expect(saved.status).toBe('draft')
  if (kind === 'projects') {
    expect(saved.repository_url).toBe('https://github.com/example/studio')
    expect(saved.website_url).toBe('https://example.com/studio')
  }
  if (kind === 'books') {
    expect(saved.author).toBe('真实作者')
    expect(saved.reading_status).toBe('completed')
    expect(saved.reading_date).toBe('2026-09-10')
    expect(saved.rating).toBe(4)
    await expect(page.locator('.writing-settings').getByText('书籍封面', { exact: true })).toBeVisible()
  }
  expect(saved.content).toContain('已保存的第一版')
  await page.getByRole('button', { name: '取消', exact: true }).click()
  expect((await (await page.request.get(`/api/v1/admin/${kind}/${id}`)).json()).status).toBe('draft')
  await expect(page.getByTestId(publishId)).toBeFocused()
  await page.getByTestId(publishId).click()
  await page.getByTestId('confirm-publish').click()
  await expect(page).not.toHaveURL(/\/admin\//)
  await expect(page.getByText('真实发布验证。', { exact: true })).toBeVisible()
  const publicPath = new URL(page.url()).pathname
  await page.goto(editPath)
  await expectHydrated(page)
  await expect(page.getByTestId(slugId)).toBeDisabled()
  await page.getByTestId(contentId).fill('# 未发布的修改\n\n新工作副本。')
  await expect(page.getByText('已自动保存', { exact: true })).toBeVisible()
  const current = await (await page.request.get(`/api/v1/admin/${kind}/${id}`)).json()
  expect(current.has_unpublished_changes).toBe(true)
  const publicResponse = await page.request.get(publicPath)
  expect(await publicResponse.text()).not.toContain('新工作副本。')
  await page.locator('.writing-mode-bar').getByRole('button', { name: '预览', exact: true }).click()
  await expect(page.locator('.writing-preview')).toContainText('新工作副本。')
  await page.locator('.writing-mode-bar').getByRole('button', { name: 'Markdown', exact: true }).click()
  for (const dark of [false, true]) {
    await page.setViewportSize({ width: 1440, height: 1000 })
    if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== dark) await page.getByRole('button', { name: '切换颜色主题' }).filter({ visible: true }).click()
    await expect(page.locator('.admin-sidebar .admin-logout')).toHaveCSS('color', dark ? 'rgb(255, 180, 171)' : 'rgb(140, 29, 24)')
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({ width, height: 900 })
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1)
      if (width !== 320) {
        await page.evaluate(() => { (document.activeElement as HTMLElement | null)?.blur(); scrollTo({ top: 0, behavior: 'instant' }) })
        await page.screenshot({ path: info.outputPath(`${singular[0]}${dark ? 'd' : 'l'}${width}.png`), fullPage: true })
        expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()).violations).toEqual([])
      }
    }
  }
  await page.getByTestId(publishId).click()
  await expect(page.getByRole('dialog', { name: '更新发布？' })).toBeVisible()
  await page.getByTestId('confirm-publish').click()
  await expect(page).not.toHaveURL(/\/admin\//)
  await expect(page.getByText('新工作副本。', { exact: true })).toBeVisible()
  expect((await page.request.get(`/api/v1/admin/${kind}/${id}`)).ok()).toBe(true)
  void headers
}

test('article', async ({ page }, info) => { await writingFlow(page, info, 'articles') })

test('book', async ({ page }, info) => { await writingFlow(page, info, 'books') })

test('project', async ({ page }, info) => { await writingFlow(page, info, 'projects') })


test('preview', async ({ page }, info) => {
  const headers = await login(page)
  const create = await page.request.post('/api/v1/admin/articles', { headers, data: { title: '真实草稿阅读', slug: `preview-${Date.now()}`, summary: '检查工作副本与公开修订的边界。', content: '# 真实草稿阅读\n\n## 阅读章节\n\n初始草稿正文。\n\n```js\nconst draft = true\n```' } })
  expect(create.status()).toBe(201)
  let article = await create.json()
  const previewPath = `/admin/articles/${article.id}/preview`
  await page.goto(previewPath)
  await expectHydrated(page)
  await expect(page.locator('.admin-core-shell')).toBeVisible()
  await expect(page.getByTestId('preview-banner')).toContainText('未公开')
  await expect(page.getByRole('heading', { level: 1 })).toHaveCount(1)
  await expect(page.locator('.reading-body')).toContainText('初始草稿正文。')
  const published = await page.request.post(`/api/v1/admin/articles/${article.id}/publish`, { headers, data: { version: article.version } })
  expect(published.ok()).toBe(true)
  article = await published.json()
  const saved = await page.request.patch(`/api/v1/admin/articles/${article.id}`, { headers, data: { version: article.version, content: '# 真实草稿阅读\n\n## 阅读章节\n\n仅工作副本中的新内容。\n\n```js\nconst draft = true\n```' } })
  expect(saved.ok()).toBe(true)
  await page.reload()
  await expectHydrated(page)
  await expect(page.getByTestId('preview-banner')).toContainText('工作副本预览')
  await expect(page.locator('.reading-body')).toContainText('仅工作副本中的新内容。')
  expect(await (await page.request.get(article.public_path)).text()).not.toContain('仅工作副本中的新内容。')
  await page.context().grantPermissions(['clipboard-read', 'clipboard-write'])
  await page.locator('.article-code-copy').click()
  await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toContain('const draft = true')
  for (const dark of [false, true]) {
    await page.setViewportSize({ width: 1440, height: 1000 })
    if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== dark) await page.getByRole('button', { name: '切换颜色主题' }).filter({ visible: true }).click()
    await expect(page.locator('.admin-sidebar .admin-logout')).toHaveCSS('color', dark ? 'rgb(255, 180, 171)' : 'rgb(140, 29, 24)')
    for (const width of [1440, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 900 })
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1)
      if (width === 1440 || width === 390) {
        await page.evaluate(() => { (document.activeElement as HTMLElement | null)?.blur(); scrollTo({ top: 0, behavior: 'instant' }) })
        await page.screenshot({ path: info.outputPath(`q${dark ? 'd' : 'l'}${width}.png`), fullPage: true })
        expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()).violations).toEqual([])
      }
    }
  }
  await page.getByRole('link', { name: '版本历史', exact: true }).click()
  await expect(page).toHaveURL(/\/revisions$/)
  await page.goto(previewPath)
  await page.getByRole('link', { name: '返回编辑', exact: true }).click()
  await expect(page.getByTestId('content')).toHaveValue(/仅工作副本中的新内容/)
})


test('revisions', async ({ page }, info) => {
  const headers = await login(page)
  let response = await page.request.post('/api/v1/admin/articles', { headers, data: { title: '真实版本历史', slug: `history-${Date.now()}`, content: '第一版内容。' } })
  expect(response.status()).toBe(201)
  let article = await response.json()
  const path = `/admin/articles/${article.id}/revisions`
  await page.goto(path)
  await expectHydrated(page)
  await expect(page.getByText('暂无发布修订。', { exact: true })).toBeVisible()
  const ids: number[] = []
  for (let i = 1; i <= 2; i++) {
    response = await page.request.patch(`/api/v1/admin/articles/${article.id}`, { headers, data: { version: article.version, content: `# 版本 ${i}\n\n第 ${i} 次发布的真实内容。` } })
    expect(response.ok()).toBe(true)
    article = await response.json()
    response = await page.request.post(`/api/v1/admin/articles/${article.id}/publish`, { headers, data: { version: article.version } })
    expect(response.ok()).toBe(true)
    article = await response.json()
    ids.push(article.current_revision_id)
  }
  await page.route(`**/api/v1/admin/articles/${article.id}/revisions?*`, route => route.fulfill({ status: 503, body: '{}' }))
  await page.reload()
  await expect(page.getByTestId('revisions-error')).toBeVisible()
  await page.unroute(`**/api/v1/admin/articles/${article.id}/revisions?*`)
  await page.getByRole('button', { name: '重新读取历史', exact: true }).click()
  await expect(page.getByTestId('revisions-error')).toHaveCount(0)
  await expect(page.getByTestId(`revision-row-${ids[1]}`)).toContainText('当前发布')
  await page.setViewportSize({ width: 390, height: 844 })
  await page.getByTestId(`view-revision-${ids[0]}`).click()
  await expect(page.getByTestId('revision-detail')).toContainText('第 1 次发布的真实内容。')
  await expect(page.getByRole('complementary', { name: '版本读取结果' })).toBeFocused()
  await expect(page.getByTestId(`view-revision-${ids[0]}`)).toHaveAttribute('aria-pressed', 'true')
  for (const dark of [false, true]) {
    await page.setViewportSize({ width: 1440, height: 1000 })
    if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== dark) await page.getByRole('button', { name: '切换颜色主题' }).filter({ visible: true }).click()
    await expect(page.locator('.admin-sidebar .admin-logout')).toHaveCSS('color', dark ? 'rgb(255, 180, 171)' : 'rgb(140, 29, 24)')
    for (const width of [1440, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 900 })
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1)
      if (width === 1440 || width === 390) {
        await page.evaluate(() => { (document.activeElement as HTMLElement | null)?.blur(); scrollTo({ top: 0, behavior: 'instant' }) })
        await page.screenshot({ path: info.outputPath(`r${dark ? 'd' : 'l'}${width}.png`), fullPage: true })
        expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()).violations).toEqual([])
      }
    }
  }
  await page.getByTestId(`compare-to-${ids[0]}`).click()
  await expect(page.getByTestId('revision-diff-panel')).toContainText('修订 #1 → #2')
  await expect(page.getByTestId('revision-diff-body')).toContainText('第 2 次发布')
  await page.getByRole('link', { name: '预览工作副本', exact: true }).click()
  await expect(page).toHaveURL(/\/preview$/)
})
