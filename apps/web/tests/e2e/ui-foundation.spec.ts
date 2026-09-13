import { expect, test } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

test('shared public foundations preserve themes, routes and keyboard navigation', async ({ page }, testInfo) => {
  await page.goto('/articles', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  for (const theme of ['light', 'dark']) {
    if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== (theme === 'dark')) {
      await page.getByRole('button', { name: '切换颜色主题' }).click()
    }
    for (const width of [320, 390, 639, 640, 768, 1024, 1279, 1280, 1440]) {
      await page.setViewportSize({ width, height: 600 })
      const metrics = await page.evaluate(() => ({
        overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
        background: getComputedStyle(document.body).backgroundImage,
        accent: getComputedStyle(document.documentElement).getPropertyValue('--ee-primary').trim(),
      }))
      expect(metrics.overflow, `${theme}/${width}`).toBe(false)
      expect(metrics.background).toBe('none')
      expect(metrics.accent).toBe(theme === 'dark' ? '#c9f24b' : '#0b5cff')
      expect(await page.getByRole('button', { name: '切换颜色主题' }).evaluate(el => el.getBoundingClientRect().height)).toBeGreaterThanOrEqual(44)
      if (width === 390 || width === 1440) {
        await page.screenshot({ path: testInfo.outputPath(`public-${theme}-${width}.png`), fullPage: true })
      }
    }
    await page.reload({ waitUntil: 'domcontentloaded' })
    await expectHydrated(page)
    expect(await page.locator('html').evaluate(el => el.classList.contains('dark'))).toBe(theme === 'dark')
  }
  for (const path of ['/', '/projects', '/books', '/archive', '/about', '/search']) {
    await page.goto(path, { waitUntil: 'domcontentloaded' })
    await expectHydrated(page)
    for (const width of [320, 1440]) {
      await page.setViewportSize({ width, height: 600 })
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), `${path}/${width}`).toBe(true)
      await expect(page.getByRole('navigation', { name: '页脚导航' }).getByRole('link', { name: 'RSS' })).toHaveAttribute('href', '/rss.xml')
    }
  }
  await page.setViewportSize({ width: 390, height: 480 })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.getByRole('button', { name: '打开主导航菜单' }).click()
  const dialog = page.getByRole('dialog', { name: '主导航' })
  const title = await page.locator('.site-menu-overlay-header').boundingBox()
  const firstLink = await dialog.getByRole('link', { name: '文章', exact: true }).boundingBox()
  expect(firstLink!.y).toBeGreaterThanOrEqual(title!.y + title!.height)
  await dialog.getByRole('link', { name: '文章', exact: true }).click()
  await expect(page).toHaveURL(/\/articles$/)
  await expect(page.locator('#main-content')).toBeFocused()
  await expect(page.locator('#main-content')).toHaveJSProperty('inert', false)
  await page.getByRole('button', { name: '打开主导航菜单' }).click()
  await expect(dialog.getByRole('link', { name: '文章', exact: true })).toHaveAttribute('aria-current', 'page')
  await dialog.getByRole('link', { name: '文章', exact: true }).click()
  await expect(dialog).toBeHidden()
  await expect(page.getByRole('button', { name: '打开主导航菜单' })).toBeFocused()
  await page.getByRole('button', { name: '打开主导航菜单' }).click()
  await page.screenshot({ path: testInfo.outputPath('menu-dark-390-short.png') })
  await dialog.getByRole('link', { name: '写作台', exact: true }).click()
  await expect(page).toHaveURL(/\/admin\/login\?returnTo=\/admin\/articles$/)
})

test('shared admin foundations keep all destinations reachable in short viewports', async ({ page }, testInfo) => {
  await page.goto('/admin/login', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  for (const theme of ['light', 'dark']) {
    if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== (theme === 'dark')) {
      await page.getByRole('button', { name: '切换颜色主题' }).click()
    }
    for (const width of [320, 390, 760, 761, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: 480 })
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), `${theme}/${width}`).toBe(true)
      if (width < 761) {
        await page.getByTestId('admin-menu-toggle').click()
        const dialog = page.getByRole('dialog', { name: '工作台导航' })
        await expect(dialog).toBeVisible()
        await expect(page.locator('#admin-main')).toHaveJSProperty('inert', true)
        const lastNav = dialog.getByRole('link', { name: '问答助手' })
        await lastNav.focus()
        await expect(lastNav).toBeInViewport()
        if (width === 390) await page.screenshot({ path: testInfo.outputPath(`admin-menu-${theme}-390.png`) })
        await page.keyboard.press('Escape')
        await expect(page.getByTestId('admin-menu-toggle')).toBeFocused()
        await expect(page.locator('#admin-main')).toHaveJSProperty('inert', false)
      }
      else {
        const nav = page.locator('.admin-sidebar')
        await expect(nav.getByRole('link', { name: '文章', exact: true })).toHaveAttribute('aria-current', 'page')
        await nav.getByRole('link', { name: '问答助手' }).focus()
        await expect(nav.getByRole('link', { name: '问答助手' })).toBeInViewport()
        await page.screenshot({ path: testInfo.outputPath(`admin-${theme}-${width}.png`) })
      }
    }
  }
  await page.setViewportSize({ width: 390, height: 480 })
  await page.getByTestId('admin-menu-toggle').click()
  await page.setViewportSize({ width: 761, height: 480 })
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(page.locator('#admin-main')).toHaveJSProperty('inert', false)
  expect(await page.evaluate(() => document.body.style.overflow)).toBe('')
})
