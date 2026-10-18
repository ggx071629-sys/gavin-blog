import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
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
const create = async (page: Page, headers: Record<string, string>, kind: string, slug: string) => {
  const response = await page.request.post(`/api/v1/admin/${kind}`, {
    headers, data: {
      title: '审查样例：写作台长标题' + '与可核对的内容'.repeat(8),
      book_title: '审查样例：读书' + '长书名'.repeat(12), author: '审查样例作者',
      slug, content: '# 起点\n\n工作副本正文。\n\n## 检查\n\n```js\nconst safe = true\n```',
    },
  })
  expect(response.status(), await response.text()).toBe(201)
  return response.json()
}
const publish = async (page: Page, headers: Record<string, string>, kind: string, item: { id: number, version: number }) => {
  const response = await page.request.post(`/api/v1/admin/${kind}/${item.id}/publish`, { headers, data: { version: item.version } })
  expect(response.ok(), await response.text()).toBe(true)
  return response.json()
}
const open = async (page: Page, path: string) => {
  await page.goto(path)
  await expectHydrated(page)
}
const noOverflow = async (page: Page, label: string) => {
  // Chromium can deliver resize before the responsive layout has painted.
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth), { message: label }).toBeLessThanOrEqual(1)
  const result = await page.evaluate(() => ({
    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    offenders: Array.from(document.querySelectorAll('body *')).filter(el => {
      const rect = el.getBoundingClientRect()
      return rect.width > 0 && rect.right > document.documentElement.clientWidth + 1
    }).slice(0, 8).map(el => [el.tagName, el.className, el.getBoundingClientRect().width]),
  }))
  expect(result.overflow, `${label}: ${JSON.stringify(result.offenders)}`).toBeLessThanOrEqual(1)
}

test('desk layout', async ({ page }, info) => {
  test.setTimeout(360_000)
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  page.on('console', message => { if (['warning', 'error'].includes(message.type())) errors.push(message.text()) })
  await open(page, '/admin/login')
  for (const theme of ['light', 'dark']) {
    if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== (theme === 'dark')) await page.getByRole('button', { name: '切换颜色主题' }).click()
    for (const width of [320, 390, 768, 1440]) {
      await page.setViewportSize({ width, height: 700 })
      await noOverflow(page, `login/${theme}/${width}`)
      if ([390, 1440].includes(width)) await page.screenshot({ path: info.outputPath(`l${theme[0]}${width}.png`), fullPage: true })
    }
  }
  const headers = await login(page)
  const article = await publish(page, headers, 'articles', await create(page, headers, 'articles', 'desk-layout-article'))
  const project = await create(page, headers, 'projects', 'desk-layout-project')
  const book = await create(page, headers, 'books', 'desk-layout-book')
  const paths = [
    '/admin/articles', '/admin/articles/new', `/admin/articles/${article.id}/edit`,
    `/admin/articles/${article.id}/preview`, `/admin/articles/${article.id}/revisions`,
    '/admin/projects', '/admin/projects/new', `/admin/projects/${project.id}/edit`,
    '/admin/books', '/admin/books/new', `/admin/books/${book.id}/edit`,
  ]
  for (const [index, path] of paths.entries()) {
    await open(page, path)
    if (await page.locator('.writing-workspace').count()) {
      const missingTargets = await page.locator('.writing-workspace [aria-controls]').evaluateAll(buttons =>
        buttons.flatMap(button => (button.getAttribute('aria-controls') || '').split(/\s+/))
          .filter(id => !id || document.querySelectorAll(`[id="${id}"]`).length !== 1))
      expect(missingTargets, `${path}/initial control targets`).toEqual([])
      await expect(page.locator('.writing-preview')).toHaveCount(1)
      await expect(page.locator('.writing-preview')).toBeHidden()
      await expect(page.locator('.writing-preview > *')).toHaveCount(0)
      const initialAxe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
      expect(initialAxe.violations, `${path}/initial Markdown`).toEqual([])
    }
    for (const theme of ['light', 'dark']) {
      if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== (theme === 'dark')) await page.getByRole('button', { name: '切换颜色主题' }).click()
      for (const width of [320, 390, 767, 768, 1024, 1440]) {
        await page.setViewportSize({ width, height: width === 320 ? 480 : 900 })
        await noOverflow(page, `${path}/${theme}/${width}`)
        if ([390, 1440].includes(width)) await page.screenshot({ path: info.outputPath(`d${index}${theme[0]}${width}.png`), fullPage: true })
      }
    }
    if (await page.locator('.writing-workspace').count()) {
      await page.setViewportSize({ width: 390, height: 480 })
      await page.emulateMedia({ reducedMotion: 'reduce' })
      const settings = page.getByRole('button', { name: '设置', exact: true })
      await settings.focus(); await page.keyboard.press('Enter')
      await expect(settings).toHaveAttribute('aria-pressed', 'true')
      await expect(page.locator('.writing-settings')).toBeVisible()
      await expect(page.locator('.writing-body')).toBeVisible()
      await noOverflow(page, `${path}/settings`)
      await page.screenshot({ path: info.outputPath(`settings-${index}.png`), fullPage: true })
      await page.getByRole('button', { name: '正文', exact: true }).click()
      await page.locator('.writing-mode-bar').getByRole('button', { name: '预览', exact: true }).click()
      await expect(page.locator('.writing-preview')).toBeVisible()
      await expect(page.locator('.writing-markdown')).toBeHidden()
      await noOverflow(page, `${path}/preview`)
      await expect(page.locator('.writing-preview > .admin-empty-note')).toBeVisible()
      await page.locator('.writing-mode-bar').getByRole('button', { name: 'Markdown', exact: true }).click()
      await expect(page.locator('.writing-markdown')).toBeVisible()
      await expect(page.locator('.writing-preview')).toHaveCount(1)
      await expect(page.locator('.writing-preview')).toBeHidden()
      await expect(page.locator('.writing-preview > *')).toHaveCount(0)
    }
    const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()
    expect(axe.violations, path).toEqual([])
  }
  expect(errors).toEqual([])
})

test('writing desk saves retries blocks conflicts and reveals hidden invalid fields', async ({ page, context }) => {
  test.setTimeout(360_000)
  const headers = await login(page)
  for (const kind of ['article', 'project', 'book']) {
    const plural = kind === 'article' ? 'articles' : `${kind}s`
    const titleId = kind === 'article' ? 'new-title' : `new-${kind}-title`
    const slugId = kind === 'article' ? 'new-slug' : `new-${kind}-slug`
    const contentId = kind === 'article' ? 'content' : `${kind}-content`
    const createId = kind === 'article' ? 'create-draft' : `create-${kind}`
    const publishId = kind === 'article' ? 'publish' : `publish-${kind}`
    await page.setViewportSize({ width: 390, height: 844 })
    await open(page, `/admin/${plural}/new`)
    await page.getByTestId(titleId).fill('纯中文标题')
    if (kind === 'book') await page.getByTestId('new-book-author').fill('审查作者')
    page.once('dialog', dialog => dialog.dismiss())
    await page.locator('.admin-back-link').click()
    await expect(page).toHaveURL(new RegExp(`/admin/${plural}/new$`))
    await page.getByTestId(createId).click()
    await expect(page.getByTestId(slugId)).toBeFocused()
    await expect(page.locator('.writing-settings')).toBeVisible()
    await page.getByTestId(slugId).fill(`desk-safety-${kind}`)
    await page.getByTestId(createId).click()
    await expect(page).toHaveURL(new RegExp(`/admin/${plural}/\\d+/edit$`))
    const editPath = new URL(page.url()).pathname
    const id = Number(editPath.split('/')[3])
    await page.getByTestId(contentId).fill('第一次公开的正文')
    await expect(page.getByText('已自动保存', { exact: true })).toBeVisible()
    await page.getByTestId(publishId).click()
    await page.getByTestId('confirm-publish').click()
    await expect(page).not.toHaveURL(/\/admin\//)
    const publicPath = new URL(page.url()).pathname
    await open(page, editPath)
    await page.getByTestId(contentId).fill('尚未发布的第二版')
    await expect(page.getByText('已自动保存', { exact: true })).toBeVisible()
    const reader = await context.newPage()
    await open(reader, publicPath)
    await expect(reader.getByText('第一次公开的正文', { exact: true })).toBeVisible()
    await expect(reader.getByText('尚未发布的第二版', { exact: true })).toHaveCount(0)
    await reader.close()
    await page.locator('.writing-mode-bar').getByRole('button', { name: '预览', exact: true }).click()
    await expect(page.locator('.writing-preview')).toContainText('尚未发布的第二版')
    await page.locator('.writing-mode-bar').getByRole('button', { name: 'Markdown', exact: true }).click()
    const endpoint = `**/api/v1/admin/${plural}/${id}`
    await page.route(endpoint, route => route.request().method() === 'PATCH' ? route.fulfill({ status: 503, contentType: 'application/json', body: '{"detail":"offline"}' }) : route.continue())
    await page.getByTestId(contentId).fill('失败后保留的最新正文')
    await expect(page.getByRole('button', { name: '重试保存' })).toBeVisible()
    const prevented = await page.evaluate(() => { const event = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(event); return event.defaultPrevented })
    expect(prevented).toBe(true)
    await page.getByRole('link', { name: '返回列表', exact: true }).click()
    await expect(page).toHaveURL(new RegExp(`${editPath}$`))
    let publishes = 0
    const countPublish = (request: import('@playwright/test').Request) => { if (request.url().endsWith(`/${id}/publish`)) publishes++ }
    page.on('request', countPublish)
    await page.getByTestId(publishId).click()
    expect(publishes).toBe(0)
    await expect(page.getByTestId(contentId)).toHaveValue('失败后保留的最新正文')
    await page.unroute(endpoint)
    await page.getByRole('button', { name: '重试保存' }).click()
    await expect(page.getByText('已自动保存', { exact: true })).toBeVisible()
    await page.route(`**/api/v1/admin/${plural}/${id}/publish`, route => route.fulfill({ status: 503, body: '{}' }))
    await page.getByTestId(publishId).click()
    await page.getByTestId('confirm-publish').click()
    await expect(page.getByText('发布失败，请稍后重试。', { exact: true })).toBeVisible()
    await expect(page).toHaveURL(new RegExp(`${editPath}$`))
    await page.unroute(`**/api/v1/admin/${plural}/${id}/publish`)
    await page.getByTestId(publishId).click()
    await page.getByTestId('confirm-publish').click()
    await expect(page).not.toHaveURL(/\/admin\//)
    await expect(page.getByText('失败后保留的最新正文', { exact: true })).toBeVisible()
    page.off('request', countPublish)
    await open(page, editPath)
    const current = await (await page.request.get(`/api/v1/admin/${plural}/${id}`)).json()
    const outside = await page.request.patch(`/api/v1/admin/${plural}/${id}`, { headers, data: { version: current.version, content: '另一窗口保存' } })
    expect(outside.ok()).toBe(true)
    await page.getByTestId(contentId).fill('当前窗口冲突内容')
    await expect(page.getByText('内容冲突', { exact: true })).toBeVisible()
    await expect(page.getByTestId(publishId)).toBeDisabled()
    await page.getByRole('link', { name: '返回列表', exact: true }).click()
    await expect(page).toHaveURL(new RegExp(`${editPath}$`))
    await expect(page.getByTestId(contentId)).toHaveValue('当前窗口冲突内容')
    // A deliberate reload is the user's explicit resolution; local text was verified above.
    page.once('dialog', dialog => dialog.accept())
    await page.reload()
    await expectHydrated(page)
    await expect(page.getByTestId(contentId)).toHaveValue('另一窗口保存')
  }
})

test('writing desk media and incomplete references remain explicit through publication', async ({ page }) => {
  const headers = await login(page)
  const target = await publish(page, headers, 'projects', await create(page, headers, 'projects', 'desk-reference-project'))
  await page.setViewportSize({ width: 390, height: 844 })
  await open(page, '/admin/articles/new')
  await page.getByTestId('new-title').fill('Desk media and references')
  await page.locator('.writing-markdown input[type=file]').setInputFiles({
    name: 'desk-pixel.png', mimeType: 'image/png',
    buffer: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=', 'base64'),
  })
  await expect(page.getByTestId('new-content')).toHaveValue(/!\[\]\(.*\/media\//)
  await page.getByTestId('create-draft').click()
  await expect(page).toHaveURL(/\/admin\/articles\/\d+\/edit$/)
  const id = Number(new URL(page.url()).pathname.split('/')[3])
  await page.locator('.writing-mode-bar').getByRole('button', { name: '预览', exact: true }).click()
  await page.getByTestId('publish').click()
  await expect(page.getByTestId('content')).toBeFocused()
  await expect(page.getByRole('alert')).toContainText('缺少 Alt 文本')
  await page.getByTestId('content').fill((await page.getByTestId('content').inputValue()).replace('![](', '![审查像素]('))
  await page.getByRole('button', { name: '设置', exact: true }).click()
  await page.getByTestId('reference-add').click()
  await expect(page.getByRole('status').filter({ hasText: '有参考资料尚未填完' })).toBeVisible()
  await page.getByRole('button', { name: '正文', exact: true }).click()
  await page.getByRole('link', { name: '返回列表', exact: true }).click()
  await expect(page.getByTestId('reference-title-0')).toBeFocused()
  await page.getByTestId('reference-target-type-0').selectOption('project')
  await page.getByTestId('reference-target-0').selectOption(String(target.id))
  await expect(page.getByText('已自动保存', { exact: true })).toBeVisible()
  const saved = await (await page.request.get(`/api/v1/admin/articles/${id}`)).json()
  expect(saved.references[0].target_type).toBe('project')
  await page.getByTestId('publish').click()
  await page.getByTestId('confirm-publish').click()
  await expect(page).not.toHaveURL(/\/admin\//)
  await expect(page.locator('.references-panel').getByRole('link', { name: target.title })).toHaveAttribute('href', target.public_path)
  await expect(page.getByRole('img', { name: '审查像素' })).toBeVisible()
})

test('writing desk previews real revisions compares and rolls back with visible failures', async ({ page }) => {
  const headers = await login(page)
  const first = await publish(page, headers, 'articles', await create(page, headers, 'articles', 'desk-revisions'))
  const updated = await page.request.patch(`/api/v1/admin/articles/${first.id}`, { headers, data: { version: first.version, content: '# 第二版\n\n明确的第二版内容。' } })
  const second = await publish(page, headers, 'articles', await updated.json())
  await open(page, `/admin/articles/${first.id}/preview`)
  await expect(page.getByTestId('preview-banner')).toContainText('工作副本预览')
  await expect(page.getByRole('heading', { level: 1 })).toHaveCount(1)
  await expect(page.locator('.reading-body')).toContainText('明确的第二版内容。')
  await open(page, `/admin/articles/${first.id}/revisions`)
  await page.getByTestId(`view-revision-${first.current_revision_id}`).click()
  await expect(page.getByTestId('revision-detail')).toContainText('工作副本正文。')
  await page.getByTestId(`compare-to-${first.current_revision_id}`).click()
  await expect(page.getByTestId('revision-diff-body')).toContainText('明确的第二版内容。')
  await page.getByTestId(`rollback-to-${first.current_revision_id}`).click()
  await expect(page.getByRole('dialog', { name: '确认回滚' })).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(page.getByTestId(`rollback-to-${first.current_revision_id}`)).toBeFocused()
  await page.getByTestId(`rollback-to-${first.current_revision_id}`).click()
  await page.getByTestId('confirm-rollback').click()
  await expect(page.getByTestId('revisions-message')).toContainText('回滚完成')
  const after = await (await page.request.get(`/api/v1/admin/articles/${first.id}`)).json()
  expect(after.current_publish_revision).toBe(second.current_publish_revision + 1)
  await open(page, after.public_path)
  await expect(page.getByText('工作副本正文。', { exact: true })).toBeVisible()
  await expect(page.getByText('明确的第二版内容。', { exact: true })).toHaveCount(0)
  await open(page, `/admin/articles/${first.id}/revisions`)
  await page.route(`**/api/v1/admin/articles/${first.id}/revisions/${first.current_revision_id}`, route => route.fulfill({ status: 503, body: '{}' }))
  await page.getByTestId(`view-revision-${first.current_revision_id}`).click()
  await expect(page.getByTestId('revisions-error')).toBeVisible()
  await expect(page.getByTestId('revision-detail')).toHaveCount(0)
})
