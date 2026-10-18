import { expect, test, type Locator, type Page } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

const setTheme = async (page: Page, dark: boolean) => {
  if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== dark) {
    await page.getByRole('button', { name: '切换颜色主题' }).filter({ visible: true }).click()
  }
}
const expectTheme = async (root: Locator, dark: boolean, surface = false) => {
  const palette = await root.evaluate((el, elevated) => {
    const shared = getComputedStyle(document.documentElement)
    const local = getComputedStyle(el)
    const tokens = [
      '--ee-canvas', '--ee-surface', '--ee-surface-low', '--ee-surface-high',
      '--ee-ink', '--ee-ink-muted', '--ee-ink-faint', '--ee-line', '--ee-line-soft',
      '--ee-primary', '--ee-primary-strong', '--ee-primary-contrast', '--ee-focus',
    ]
    const probe = document.createElement('span')
    document.body.append(probe)
    probe.style.color = shared.getPropertyValue('--ee-ink').trim()
    probe.style.backgroundColor = shared.getPropertyValue(elevated ? '--ee-surface' : '--ee-canvas').trim()
    const expected = { color: getComputedStyle(probe).color, background: getComputedStyle(probe).backgroundColor }
    probe.remove()
    return {
      ...expected,
      mismatches: tokens.filter(token => local.getPropertyValue(token).trim() !== shared.getPropertyValue(token).trim()),
      primary: local.getPropertyValue('--ee-primary').trim(),
    }
  }, surface)
  expect(palette.mismatches).toEqual([])
  expect(palette.primary).toBe(dark ? '#c9f24b' : '#0b5cff')
  await expect(root).toHaveCSS('color', palette.color)
  await expect(root).toHaveCSS('background-color', palette.background)
  await expect(root).toHaveCSS('font-family', /Inter.*Noto Sans SC/)
}

test('theme', async ({ page }, info) => {
  const externalAssets: string[] = []
  page.on('request', request => {
    if (['font', 'image'].includes(request.resourceType()) && !request.url().startsWith(new URL(page.url()).origin)) externalAssets.push(request.url())
  })
  const publicColors: string[] = []
  await page.goto('/')
  await expectHydrated(page)
  for (const dark of [false, true]) {
    await setTheme(page, dark)
    publicColors.push(await page.locator('html').evaluate(el => getComputedStyle(el).getPropertyValue('--ee-primary')))
  }
  await page.goto('/admin/login')
  await expectHydrated(page)
  for (const dark of [false, true]) {
    await setTheme(page, dark)
    await expectTheme(page.locator('.admin-login-shell'), dark)
    await expect(page.getByRole('heading', { level: 1 })).toHaveCSS('font-family', /Inter.*Noto Sans SC/)
    await expect(page.getByTestId('username')).toHaveCSS('min-height', '48px')
    await expect(page.getByTestId('username')).toHaveCSS('border-radius', '7px')
    await page.screenshot({ path: info.outputPath(`login-${dark ? 'dark' : 'light'}.png`) })
  }
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  const headers = { 'X-CSRF-Token': (await page.context().cookies()).find(c => c.name === 'gavin_csrf')!.value }
  const created = await page.request.post('/api/v1/admin/articles', { headers, data: { title: '主题验收', slug: 'studio-theme', content: '第一版' } })
  expect(created.status()).toBe(201)
  const draft = await created.json()
  const firstResponse = await page.request.post(`/api/v1/admin/articles/${draft.id}/publish`, { headers, data: { version: draft.version } })
  expect(firstResponse.ok()).toBe(true)
  const first = await firstResponse.json()
  const update = await page.request.patch(`/api/v1/admin/articles/${first.id}`, { headers, data: { version: first.version, content: '第二版' } })
  expect(update.ok()).toBe(true)
  const second = await update.json()
  expect((await page.request.post(`/api/v1/admin/articles/${first.id}/publish`, { headers, data: { version: second.version } })).ok()).toBe(true)
  await page.goto(`/admin/articles/${first.id}/revisions`)
  await expectHydrated(page)
  for (const dark of [false, true]) {
    await setTheme(page, dark)
    await expectTheme(page.locator('.admin-core-shell'), dark)
    await page.getByTestId(`rollback-to-${first.current_revision_id}`).click()
    const dialog = page.getByRole('dialog', { name: '确认回滚' })
    await expectTheme(dialog, dark, true)
    await expect(dialog.getByRole('heading')).toHaveCSS('font-family', /Inter.*Noto Sans SC/)
    await expect(dialog.getByTestId('confirm-rollback')).toHaveCSS('min-height', '48px')
    await expect(dialog.getByRole('button', { name: '取消', exact: true })).toHaveCSS('min-height', '48px')
    await page.screenshot({ path: info.outputPath(`dialog-${dark ? 'dark' : 'light'}.png`) })
    await page.keyboard.press('Escape')
    await expect(dialog).toHaveCount(0)
  }
  await page.setViewportSize({ width: 390, height: 700 })
  await page.getByTestId(`rollback-to-${first.current_revision_id}`).click()
  await expect(page.getByTestId('confirm-rollback')).toHaveCSS('min-height', '44px')
  await page.keyboard.press('Escape')
  await page.setViewportSize({ width: 1280, height: 720 })
  await page.goto('/')
  await expectHydrated(page)
  for (const [index, dark] of [false, true].entries()) {
    await setTheme(page, dark)
    expect(await page.locator('html').evaluate(el => getComputedStyle(el).getPropertyValue('--ee-primary'))).toBe(publicColors[index])
    expect(await page.locator('main').evaluate(el => getComputedStyle(el).getPropertyValue('--studio-primary'))).toBe('')
  }
  expect(externalAssets).toEqual([])
})
