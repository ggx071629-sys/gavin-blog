import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

test('articles', async ({ page }, info) => {
  test.setTimeout(240_000)
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto('/admin/login')
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  const headers = { 'X-CSRF-Token': (await page.context().cookies()).find(c => c.name === 'gavin_csrf')!.value }
  const prefix = `list-${Date.now()}`
  let id = 0
  for (let n = 0; n < 23; n++) {
    const response = await page.request.post('/api/v1/admin/articles', { headers, data: { title: `${prefix} 记录 ${n}`, slug: `${prefix}-${n}`, content: '# 初稿' } })
    expect(response.status()).toBe(201)
    const item = await response.json()
    if (n === 22) {
      id = item.id
      const published = await (await page.request.post(`/api/v1/admin/articles/${id}/publish`, { headers, data: { version: item.version } })).json()
      expect((await page.request.patch(`/api/v1/admin/articles/${id}`, { headers, data: { version: published.version, title: `${prefix} ${'长标题与真实修改'.repeat(12)}` } })).ok()).toBe(true)
    }
  }
  await page.goto(`/admin/articles?q=${prefix}`)
  await expectHydrated(page)
  await expect(page.locator('.content-row')).toHaveCount(20)
  await expect(page.locator('.list-pagination')).toContainText('共 23 项')
  await expect(page.locator('.list-attention')).toContainText('本页 1 项')
  await page.getByTestId('pagination-next').click()
  await expect(page.locator('.content-row')).toHaveCount(3)
  await expect(page).toHaveURL(/page=2/)
  await page.locator('.list-filters').getByRole('link', { name: /草稿/ }).click()
  await expect(page).not.toHaveURL(/page=/)
  await expect(page.locator('.list-pagination')).toContainText('共 22 项')
  await expect(page.getByTestId('pagination-next')).toHaveAttribute('href', /status=draft/)
  await page.getByLabel('搜索标题').fill('no-matches-unique')
  await page.getByRole('button', { name: '搜索', exact: true }).click()
  await expect(page.getByRole('heading', { name: '没有匹配的内容' })).toBeVisible()
  await page.getByRole('link', { name: '清除搜索与筛选' }).click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  await page.goto(`/admin/articles?q=${prefix}`)
  await expectHydrated(page)
  for (const dark of [false, true]) {
    await page.setViewportSize({ width: 1440, height: 1058 })
    if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== dark) await page.getByRole('button', { name: '切换颜色主题' }).filter({ visible: true }).click()
    await expect(page.locator('.admin-sidebar .admin-logout')).toHaveCSS('color', dark ? 'rgb(255, 180, 171)' : 'rgb(140, 29, 24)')
    for (const width of [1440, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 900 })
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1)
      if ([1440, 390].includes(width)) {
        await page.screenshot({ path: info.outputPath(`a${dark ? 'd' : 'l'}${width}.png`) })
        expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()).violations).toEqual([])
      }
    }
  }
  await page.locator('.content-row').first().getByRole('button', { name: /更多操作/ }).click()
  await expect(page.getByRole('dialog').getByRole('link', { name: '预览草稿' })).toHaveAttribute('href', `/admin/articles/${id}/preview`)
  await expect(page.getByRole('dialog').getByRole('link', { name: '版本历史' })).toHaveAttribute('href', `/admin/articles/${id}/revisions`)
  page.once('dialog', dialog => dialog.dismiss())
  await page.getByRole('button', { name: '移入回收站', exact: true }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  page.once('dialog', dialog => dialog.accept())
  await page.getByRole('button', { name: '移入回收站', exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(page.locator('.list-pagination')).toContainText('共 22 项')
  await expect(page.locator('.content-row')).toHaveCount(20)
  await page.route('**/api/v1/admin/articles/query?**', route => route.fulfill({ status: 503, body: '{}' }))
  await page.getByLabel('搜索标题').fill('failure-test')
  await page.getByRole('button', { name: '搜索', exact: true }).click()
  await expect(page.getByRole('heading', { name: '列表读取失败' })).toBeVisible()
  await expect(page.locator('.content-row')).toHaveCount(0)
  await page.unroute('**/api/v1/admin/articles/query?**')
  await page.getByRole('button', { name: '重新读取' }).click()
  await expect(page.getByRole('heading', { name: '没有匹配的内容' })).toBeVisible()
  expect(errors).toEqual([])
})

test('books', async ({ page }, info) => {
  await page.goto('/admin/login')
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  const headers = { 'X-CSRF-Token': (await page.context().cookies()).find(c => c.name === 'gavin_csrf')!.value }
  const author = `作者-${Date.now()}`
  const created = await page.request.post('/api/v1/admin/books', { headers, data: { book_title: '数据密集型应用设计' + '长书名'.repeat(10), author, slug: `book-${Date.now()}`, reading_status: 'reading', content: '# 真实读书笔记' } })
  expect(created.status()).toBe(201)
  const item = await created.json()
  await page.goto('/admin/books')
  await expectHydrated(page)
  await page.getByLabel('搜索书名或作者').fill(author)
  await page.getByRole('button', { name: '搜索', exact: true }).click()
  await expect(page.locator('.content-row')).toHaveCount(1)
  await expect(page.locator('.content-row')).toContainText(author)
  await expect(page.locator('.content-row')).toContainText('在读')
  await expect(page.locator('.list-pagination')).toContainText('共 1 项')
  for (const dark of [false, true]) {
    await page.setViewportSize({ width: 1440, height: 900 })
    if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== dark) await page.getByRole('button', { name: '切换颜色主题' }).filter({ visible: true }).click()
    await expect(page.locator('.admin-sidebar .admin-logout')).toHaveCSS('color', dark ? 'rgb(255, 180, 171)' : 'rgb(140, 29, 24)')
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({ width, height: 900 })
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1)
      if (width !== 320) {
        await page.screenshot({ path: info.outputPath(`b${dark ? 'd' : 'l'}${width}.png`), fullPage: true })
        expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()).violations).toEqual([])
      }
    }
  }
  await expect(page.locator('.list-edit')).toHaveAttribute('href', `/admin/books/${item.id}/edit`)
  await page.locator('.list-more').click()
  await expect(page.getByRole('dialog').getByRole('link', { name: '版本历史' })).toHaveCount(0)
  await page.route(`**/api/v1/admin/books/${item.id}`, route => route.fulfill({ status: 503, body: '{}' }))
  page.once('dialog', dialog => dialog.accept())
  await page.getByRole('button', { name: '移入回收站', exact: true }).click()
  await expect(page.getByRole('dialog').getByRole('alert')).toContainText('删除失败')
  await page.unroute(`**/api/v1/admin/books/${item.id}`)
  page.once('dialog', dialog => dialog.accept())
  await page.getByRole('button', { name: '移入回收站', exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: '没有匹配的内容' })).toBeVisible()
})

test('projects', async ({ page }, info) => {
  await page.goto('/admin/login')
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  const headers = { 'X-CSRF-Token': (await page.context().cookies()).find(c => c.name === 'gavin_csrf')!.value }
  const title = `项目-${Date.now()}`
  const response = await page.request.post('/api/v1/admin/projects', { headers, data: { title, slug: `project-${Date.now()}`, summary: 'Nuxt 与 FastAPI 的技术选择记录', repository_url: 'https://github.com/example/project', website_url: 'https://example.com/', content: '# 项目' } })
  expect(response.status()).toBe(201)
  const item = await response.json()
  await page.goto('/admin/projects')
  await expectHydrated(page)
  await page.getByLabel('搜索标题').fill(title)
  await page.getByRole('button', { name: '搜索', exact: true }).click()
  await expect(page.locator('.content-row')).toHaveCount(1)
  await expect(page.locator('.content-row')).toContainText('Nuxt 与 FastAPI')
  await expect(page.locator('.content-row').getByRole('link', { name: '仓库' })).toHaveAttribute('href', 'https://github.com/example/project')
  await expect(page.locator('.content-row').getByRole('link', { name: '站点' })).toHaveAttribute('rel', 'noopener noreferrer')
  for (const dark of [false, true]) {
    await page.setViewportSize({ width: 1440, height: 900 })
    if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== dark) await page.getByRole('button', { name: '切换颜色主题' }).filter({ visible: true }).click()
    await expect(page.locator('.admin-sidebar .admin-logout')).toHaveCSS('color', dark ? 'rgb(255, 180, 171)' : 'rgb(140, 29, 24)')
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({ width, height: 900 })
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1)
      if (width !== 320) {
        await page.screenshot({ path: info.outputPath(`p${dark ? 'd' : 'l'}${width}.png`), fullPage: true })
        expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze()).violations).toEqual([])
      }
    }
  }
  await expect(page.locator('.list-edit')).toHaveAttribute('href', `/admin/projects/${item.id}/edit`)
  await page.locator('.list-filters').getByRole('link', { name: /已发布/ }).click()
  await expect(page.locator('.list-pagination')).toContainText('共 0 项')
  await page.locator('.list-filters').getByRole('link', { name: /草稿/ }).click()
  await expect(page.locator('.content-row')).toHaveCount(1)
  await page.locator('.list-more').click()
  await expect(page.getByRole('dialog').getByRole('link', { name: '版本历史' })).toHaveCount(0)
  page.once('dialog', dialog => dialog.accept())
  await page.getByRole('button', { name: '移入回收站', exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(page.locator('.list-pagination')).toContainText('共 0 项')
})

test('states', async ({ page }) => {
  test.setTimeout(240_000)
  await page.goto('/admin/login')
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  const headers = { 'X-CSRF-Token': (await page.context().cookies()).find(c => c.name === 'gavin_csrf')!.value }
  for (const kind of ['articles', 'books', 'projects']) {
    const keyword = `state-${kind}-${Date.now()}`
    for (let index = 0; index < 22; index++) {
      const response = await page.request.post(`/api/v1/admin/${kind}`, { headers, data: { title: `${keyword} ${index}`, book_title: `${keyword} ${index}`, author: '查询作者', slug: `${keyword}-${index}`, content: '# 分页验证' } })
      expect(response.status()).toBe(201)
    }
    await page.goto(`/admin/${kind}?q=${keyword}`)
    await expectHydrated(page)
    await expect(page.locator('.content-row')).toHaveCount(20)
    await page.getByTestId('pagination-next').click()
    await expect(page.locator('.content-row')).toHaveCount(2)
    await expect(page).toHaveURL(/page=2/)
    await page.locator('.list-filters').getByRole('link', { name: /草稿/ }).click()
    await expect(page.locator('.content-row')).toHaveCount(20)
    await expect(page).not.toHaveURL(/page=/)
    await page.goBack()
    await expect(page).toHaveURL(/page=2/)
    await expect(page.locator('.content-row')).toHaveCount(2)
    await page.setViewportSize({ width: 390, height: 844 })
    const more = page.locator('.list-more').first()
    await more.click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(more).toBeFocused()
    await expect(page.locator('body')).not.toHaveCSS('overflow', 'hidden')
    let release!: () => void
    const gate = new Promise<void>(resolve => { release = resolve })
    await page.route(`**/api/v1/admin/${kind}/query?**`, async route => { await gate; await route.fulfill({ status: 503, body: '{}' }) })
    await page.getByRole('searchbox').fill('loading-state')
    await page.getByRole('button', { name: '搜索', exact: true }).click()
    await expect(page.getByRole('status').filter({ hasText: '正在读取内容' })).toBeVisible()
    await expect(page.locator('.content-row')).toHaveCount(0)
    release()
    await expect(page.getByRole('heading', { name: '列表读取失败' })).toBeVisible()
    await page.unroute(`**/api/v1/admin/${kind}/query?**`)
    await page.getByRole('button', { name: '重新读取' }).click()
    await expect(page.getByRole('heading', { name: '没有匹配的内容' })).toBeVisible()
    await page.getByRole('link', { name: '清除搜索与筛选' }).click()
    await expect(page).toHaveURL(new RegExp(`/admin/${kind}$`))
    await expect(page.locator('.content-row')).toHaveCount(20)
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1)
  }
})
