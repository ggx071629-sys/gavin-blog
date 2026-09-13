import { expect, test } from '@playwright/test'
import { join } from 'node:path'
import { expectHydrated as waitForHydration } from '../support/hydration'

const login = async (page: import('@playwright/test').Page) => {
  await page.goto('/admin/login', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  await expect(page.getByTestId('login')).toBeEnabled()
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
}

test('about editor keeps drafts private until explicit publish', async ({ page }) => {
  const statement = `ABOUT-E2E-DRAFT-${Date.now()} <em>纯文本</em>`
  await login(page)
  await page.goto('/admin/about', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  await expect(page.getByRole('heading', { name: '关于页内容' })).toBeVisible()
  await expect(page.getByRole('link', { name: '前往个人名片' })).toHaveAttribute('href', '/admin/profile')
  await expect(page.getByTestId('profile-name')).toHaveCount(0)
  await page.getByTestId('about-statement').fill(statement)
  const topic = `TOPIC-${Date.now()}`
  await page.getByTestId('about-topic-input').fill(topic)
  await page.getByTestId('about-topic-add').click()

  await page.getByTestId('about-preview-open').click()
  await waitForHydration(page)
  await expect(page.getByTestId('about-preview-banner')).toContainText('工作副本预览')
  await expect(page.locator('body')).toContainText(statement)

  await page.goto('/about', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  await expect(page.locator('body')).not.toContainText(statement)
  await expect(page.locator('body')).not.toContainText(topic)
  expect((await (await page.request.get('/api/v1/about-page')).json()).statement).not.toBe(statement)

  await page.goto('/admin/about', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  await expect(page.getByTestId('about-statement')).toHaveValue(statement)
  await page.getByTestId('about-publish').click()
  await expect(page).toHaveURL(url => url.pathname === '/about')
  await waitForHydration(page)
  expect((await (await page.request.get('/api/v1/about-page')).json()).statement).toBe(statement)
  await expect(page.getByRole('region', { name: '自述与写作主题' })).toContainText(statement)
  await expect(page.getByRole('region', { name: '自述与写作主题' })).toContainText(topic)
  await expect(page.getByRole('region', { name: '自述与写作主题' }).locator('em')).toHaveCount(0)
})

test('about autosave keeps an unsubmitted tag draft until it is added', async ({ page }) => {
  await login(page)
  await page.goto('/admin/about', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  const capabilityCard = page.getByTestId('about-capability-card').first()
  await expect(capabilityCard).toBeVisible()
  const tagInput = capabilityCard.getByTestId('about-tag-input')

  let releasePatch!: () => void
  const patchGate = new Promise<void>((resolve) => { releasePatch = resolve })
  let markPatchStarted!: () => void
  const patchStarted = new Promise<void>((resolve) => { markPatchStarted = resolve })
  await page.route('**/api/v1/admin/about-page', async (route) => {
    if (route.request().method() !== 'PATCH') return route.continue()
    markPatchStarted()
    await patchGate
    await route.continue()
  })

  await page.getByTestId('about-statement').fill(`草稿保护-${Date.now()}`)
  await patchStarted
  await tagInput.fill('尚未提交的新标签')
  releasePatch()

  await expect(page.locator('.save-state')).toHaveText('工作副本已保存')
  await expect(tagInput).toHaveValue('尚未提交的新标签')

  await capabilityCard.getByTestId('about-tag-add').click()
  await expect(capabilityCard).toContainText('尚未提交的新标签')
  await expect(tagInput).toHaveValue('')
})

test('about tag drafts follow their capability across reorder and removal', async ({ page }) => {
  await login(page)
  await page.goto('/admin/about', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  const cards = page.getByTestId('about-capability-card')
  const initial = await cards.count()
  await page.getByTestId('about-capability-add').click()
  await page.getByTestId('about-capability-add').click()
  await expect(cards).toHaveCount(initial + 2)

  const penultimate = cards.nth(initial)
  const last = cards.nth(initial + 1)
  await penultimate.getByTestId('about-capability-title').fill('倒数第二领域')
  await last.getByTestId('about-capability-title').fill('尾部领域')
  await last.getByTestId('about-tag-input').fill('跟随草稿')

  await last.getByTestId('about-capability-up').click()
  await expect(cards.nth(initial).getByTestId('about-capability-title')).toHaveValue('尾部领域')
  await expect(cards.nth(initial).getByTestId('about-tag-input')).toHaveValue('跟随草稿')
  await expect(cards.nth(initial + 1).getByTestId('about-capability-title')).toHaveValue('倒数第二领域')
  await expect(cards.nth(initial + 1).getByTestId('about-tag-input')).toHaveValue('')

  await cards.nth(initial).getByTestId('about-capability-remove').click()
  await expect(cards.nth(initial).getByTestId('about-capability-title')).toHaveValue('倒数第二领域')
  await expect(cards.nth(initial).getByTestId('about-tag-input')).toHaveValue('')
})

test('about editor exposes history and rollback actions in the writing desk', async ({ page }) => {
  await login(page)
  await page.goto('/admin/about/revisions', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  await expect(page.getByRole('heading', { name: '关于页版本历史' })).toBeVisible()
  await expect(page.getByTestId('about-revision-list')).toContainText('修订 1')
  const viewButton = page.getByTestId('about-revision-view').first()
  await viewButton.click()
  await expect(page.getByTestId('about-revision-detail')).toBeVisible()
  await expect(page.getByTestId('about-revision-preview-toggle')).toBeVisible()
})

test('about editor supports ten cards per section and re-enables add after removal', async ({ page }, testInfo) => {
  await login(page)
  await page.goto('/admin/about', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  for (const section of ['capability', 'now']) {
    const cards = page.getByTestId(`about-${section}-card`)
    const add = page.getByTestId(`about-${section}-add`)
    const fillLast = async () => {
      if (section === 'capability') {
        await cards.last().getByTestId('about-capability-title').fill(`领域 ${await cards.count()}`)
        await cards.last().getByTestId('about-capability-description').fill('新增领域说明')
      }
      else {
        await cards.last().getByTestId('about-now-label').fill(`动态 ${await cards.count()}`)
      }
    }
    while (await cards.count() < 10) {
      await add.click()
      await fillLast()
    }
    await expect(add).toBeDisabled()
    await cards.last().getByTestId(`about-${section}-remove`).click()
    await expect(cards).toHaveCount(9)
    await expect(add).toBeEnabled()
    await add.click()
    await fillLast()
    await expect(cards).toHaveCount(10)
    await expect(add).toBeDisabled()
  }
  await expect(page.locator('#about-capabilities-title')).toContainText('10 / 10')
  await expect(page.locator('#about-now-title')).toContainText('10 / 10')
  await page.getByTestId('about-preview-open').click()
  await expect(page).toHaveURL(/\/admin\/about\/preview$/)
  await waitForHydration(page)
  await expect(page.locator('.about-capability')).toHaveCount(10)
  await expect(page.locator('.ae-now > a')).toHaveCount(10)
  await page.goto('/admin/about', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  await expect(page.getByTestId('about-capability-card')).toHaveCount(10)
  await expect(page.getByTestId('about-now-card')).toHaveCount(10)
  await page.getByTestId('about-publish').click()
  await expect(page).toHaveURL(url => url.pathname === '/about')
  await waitForHydration(page)
  await expect(page.locator('.about-capability')).toHaveCount(10)
  await expect(page.locator('.ae-now > a')).toHaveCount(10)
  const icons = page.locator('.about-capability .geometric-mark')
  await expect(icons).toHaveCount(10)
  const signatures = await icons.evaluateAll(elements => elements.map(element =>
    [...element.querySelectorAll('path')].map(path => path.getAttribute('d')).join('|'),
  ))
  expect(new Set(signatures).size).toBe(10)
  for (let index = 0; index < 10; index++) {
    const icon = icons.nth(index)
    await expect(icon).toHaveAttribute('data-variant', String(index))
    await page.locator('.about-capability').nth(index).hover()
    await expect(icon).toHaveAttribute('data-active', 'true')
    await expect.poll(() => icon.locator('path').evaluateAll(paths =>
      paths.some(path => getComputedStyle(path).transform !== 'none'),
    )).toBe(true)
    await page.mouse.move(0, 0)
    await expect(icon).toHaveAttribute('data-active', 'false')
    await expect.poll(() => icon.locator('path').evaluateAll(paths =>
      paths.every(path => getComputedStyle(path).transform === 'none'),
    )).toBe(true)
  }
  await page.emulateMedia({ reducedMotion: 'reduce' })
  for (let index = 0; index < 10; index++) {
    await page.locator('.about-capability').nth(index).hover()
    expect(await icons.nth(index).locator('path').evaluateAll(paths =>
      paths.every(path => getComputedStyle(path).transform === 'none'
        && parseFloat(getComputedStyle(path).transitionDuration) <= 0.00001),
    )).toBe(true)
  }
  await page.emulateMedia({ reducedMotion: 'no-preference' })
  await page.mouse.move(0, 0)
  await page.locator('.about-capability').first().dispatchEvent('pointerenter', { pointerType: 'touch' })
  await expect(icons.first()).toHaveAttribute('data-active', 'false')
  await page.evaluate(() => window.scrollTo(0, 0))
  // Keep the exported diagnostic path below Windows' legacy path limit.
  await page.screenshot({ path: join(testInfo.project.outputDir, 'about-icons.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
})


test('studio about editor', async ({ page }, info) => {
  test.setTimeout(180_000)
  await login(page)
  await page.goto('/admin/about')
  await waitForHydration(page)
  await expect(page.getByTestId('about-publication-state')).toContainText('草稿自动保存')
  await expect(page.getByTestId('profile-name')).toHaveCount(0)
  const marker = `阶段五引言-${Date.now()}`
  await page.getByTestId('about-statement').fill(marker)
  for (const section of ['capability', 'now']) {
    const cards = page.getByTestId(`about-${section}-card`)
    const add = page.getByTestId(`about-${section}-add`)
    while (await cards.count() < 10) {
      await add.click()
      if (section === 'capability') {
        await cards.last().getByTestId('about-capability-title').fill(`领域 ${await cards.count()}`)
        await cards.last().getByTestId('about-capability-description').fill('能力描述')
      }
      else await cards.last().getByTestId('about-now-label').fill(`动态 ${await cards.count()}`)
    }
    await expect(add).toBeDisabled()
    const lastValue = await cards.last().getByTestId(section === 'capability' ? 'about-capability-title' : 'about-now-label').inputValue()
    await cards.last().getByTestId(`about-${section}-up`).click()
    await expect(cards.nth(8).getByTestId(section === 'capability' ? 'about-capability-title' : 'about-now-label')).toHaveValue(lastValue)
    await cards.last().getByTestId(`about-${section}-remove`).click()
    await expect(add).toBeEnabled()
    // Retain a realistic compact populated page for visual inspection.
    while (await cards.count() > 2) await cards.last().getByTestId(`about-${section}-remove`).click()
  }
  await expect(page.getByText('工作副本已保存', { exact: true })).toBeVisible()
  await expect.poll(async () => {
    const draft = await (await page.request.get('/api/v1/admin/about-page')).json()
    return { statement: draft.content.statement, capabilities: draft.content.capabilities.length, now: draft.content.now.length }
  }).toEqual({ statement: marker, capabilities: 2, now: 2 })
  expect((await (await page.request.get('/api/v1/about-page')).json()).statement).not.toBe(marker)
  for (const dark of [false, true]) {
    await page.setViewportSize({ width: 1440, height: 1000 })
    if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== dark) await page.getByRole('button', { name: '切换颜色主题' }).filter({ visible: true }).click()
    for (const width of [1440, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 900 })
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1)
      if ([1440, 390].includes(width)) {
        await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }))
        await page.screenshot({ path: join(info.project.outputDir, `ae${dark ? 'd' : 'l'}${width}.png`), fullPage: true })
      }
    }
  }
  await page.getByTestId('about-publish').click()
  await expect(page).toHaveURL(url => url.pathname === '/about')
  expect((await (await page.request.get('/api/v1/about-page')).json()).statement).toBe(marker)
})


test('ap', async ({ page }, info) => {
  test.setTimeout(120_000)
  await login(page)
  await page.goto('/admin/profile'); await waitForHydration(page)
  await page.getByTestId('profile-name').fill('共用身份')
  await page.getByTestId('profile-city').fill('隐藏位置')
  await page.getByTestId('profile-city-visible').uncheck()
  await page.getByTestId('profile-save').click()
  await expect(page.getByText('个人名片已更新')).toBeVisible()
  await page.goto('/admin/about'); await waitForHydration(page)
  await page.getByTestId('about-statement').fill('草稿字段核对')
  await page.getByTestId('about-preview-open').click()
  await expect(page).toHaveURL(/\/admin\/about\/preview$/)
  await expect(page.locator('.admin-core-shell')).toBeVisible()
  await expect(page.getByTestId('about-preview-banner')).toContainText('工作副本预览')
  await expect(page.getByTestId('about-preview-statement')).toHaveText('草稿字段核对')
  await expect(page.getByTestId('profile-card')).toContainText('共用身份')
  await expect(page.getByTestId('profile-card')).not.toContainText('隐藏位置')
  expect((await (await page.request.get('/api/v1/about-page')).json()).statement).not.toBe('草稿字段核对')
  for (const dark of [false, true]) {
    await page.setViewportSize({ width: 1440, height: 1000 })
    if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== dark) await page.getByRole('button', { name: '切换颜色主题' }).filter({ visible: true }).click()
    for (const width of [1440, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 900 })
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1)
      if ([1440, 390].includes(width)) {
        await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }))
        await page.screenshot({ path: join(info.project.outputDir, `ap${dark ? 'd' : 'l'}${width}.png`), fullPage: true })
      }
    }
  }
  await page.getByRole('link', { name: '返回编辑', exact: true }).click()
  await expect(page.getByTestId('about-statement')).toHaveValue('草稿字段核对')
})


test('ah', async ({ page }, info) => {
  test.setTimeout(180_000)
  await login(page)
  const headers = { 'X-CSRF-Token': (await page.context().cookies()).find(c => c.name === 'gavin_csrf')!.value }
  let about = await (await page.request.get('/api/v1/admin/about-page')).json()
  const before = await (await page.request.get('/api/v1/admin/about-page/revisions')).json()
  for (let i = 0; i < 21; i++) {
    const saved = await page.request.patch('/api/v1/admin/about-page', { headers, data: { version: about.version, content: { ...about.content, statement: `历史内容 ${i}` } } })
    expect(saved.ok()).toBe(true); about = await saved.json()
    const published = await page.request.post('/api/v1/admin/about-page/publish', { headers, data: { version: about.version } })
    expect(published.ok()).toBe(true); about = await published.json()
  }
  await page.goto('/admin/about/revisions'); await waitForHydration(page)
  await expect(page.getByTestId('about-revision-view')).toHaveCount(20)
  await page.getByRole('button', { name: '加载更多版本' }).click()
  await expect(page.getByTestId('about-revision-view')).toHaveCount(Math.min(40, before.total + 21))
  const older = page.getByTestId('about-revision-list').locator('li').nth(1)
  await page.route('**/api/v1/admin/about-page/revisions/*', route => route.request().method() === 'GET' ? route.fulfill({ status: 503, json: { detail: '读取失败' } }) : route.continue())
  await older.getByTestId('about-revision-view').click()
  await expect(page.getByRole('alert')).toContainText('读取失败')
  await expect(page.getByTestId('about-revision-detail')).toHaveCount(0)
  await page.unroute('**/api/v1/admin/about-page/revisions/*')
  await older.getByTestId('about-revision-view').click()
  await expect(page.getByTestId('about-snapshot-statement')).toHaveText('历史内容 19')
  await expect(page.getByRole('alert')).toHaveCount(0)
  await older.getByTestId('about-revision-compare').click()
  await expect(page.getByTestId('about-revision-diff-panel')).toContainText('历史内容 19')
  await expect(page.getByTestId('about-revision-diff-panel')).toContainText('历史内容 20')
  await older.getByTestId('about-revision-rollback').click()
  await page.getByRole('dialog').getByRole('button', { name: '取消', exact: true }).click()
  expect((await (await page.request.get('/api/v1/admin/about-page')).json()).current_revision_id).toBe(about.current_revision_id)
  await older.getByTestId('about-revision-rollback').click()
  await page.getByTestId('about-rollback-confirm').click()
  await expect(page.getByRole('status')).toContainText('已创建回滚修订')
  expect((await (await page.request.get('/api/v1/about-page')).json()).statement).toBe('历史内容 19')
  const after = await (await page.request.get('/api/v1/admin/about-page/revisions')).json()
  expect(after.total).toBe(before.total + 22)
  await page.getByTestId('about-revision-view').first().click()
  for (const dark of [false, true]) {
    await page.setViewportSize({ width: 1440, height: 1000 })
    if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== dark) await page.getByRole('button', { name: '切换颜色主题' }).filter({ visible: true }).click()
    for (const width of [1440, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 900 })
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1)
      if ([1440, 390].includes(width)) {
        await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }))
        await page.screenshot({ path: join(info.project.outputDir, `ah${dark ? 'd' : 'l'}${width}.png`) })
      }
    }
  }
  await page.getByTestId('about-revision-view').first().click()
  await expect(page.locator('aside[tabindex="-1"]')).toBeFocused()
})
