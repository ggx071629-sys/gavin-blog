import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

test('shell', async ({ page }, info) => {
  test.setTimeout(240_000)
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  page.on('console', message => { if (['warning', 'error'].includes(message.type())) errors.push(message.text()) })
  const failedIcons: string[] = []
  page.on('response', response => { if (response.url().includes('/studio/icons/') && response.status() >= 400) failedIcons.push(`${response.status()} ${response.url()}`) })
  await page.goto('/admin/login')
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  for (const dark of [false, true]) {
    if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== dark) {
      await page.getByRole('button', { name: '切换颜色主题' }).filter({ visible: true }).click()
    }
    for (const width of [320, 390, 760, 761, 1024, 1280, 1440, 1487]) {
      await page.setViewportSize({ width, height: width === 320 ? 480 : 900 })
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1)
      const mobile = width <= 760
      const nav = mobile ? page.locator('#admin-mobile-drawer') : page.locator('.admin-sidebar')
      if (mobile) {
        await page.getByTestId('admin-menu-toggle').click()
        await expect(nav).toBeVisible()
        await expect(page.locator('#admin-main')).toHaveJSProperty('inert', true)
        const close = nav.getByRole('button', { name: '关闭导航菜单' })
        await expect(close).toBeFocused()
        await page.keyboard.press('Shift+Tab')
        await expect(nav.getByRole('button', { name: '退出', exact: true })).toBeFocused()
        await page.keyboard.press('Tab')
        await expect(close).toBeFocused()
      }
      else {
        await expect(nav).toHaveCSS('width', width <= 1300 ? '230px' : '254px')
        await expect(page.getByTestId('admin-menu-toggle')).toBeHidden()
        if (width >= 1440) expect(await page.locator('#admin-main').evaluate(el => el.getBoundingClientRect().left + parseFloat(getComputedStyle(el).paddingLeft))).toBe(290)
      }
      await expect(nav.locator('.admin-nav-link')).toHaveCount(9)
      await expect(nav.locator('.admin-nav-link .studio-icon')).toHaveCount(9)
      await expect(nav.locator('.admin-nav-link[aria-current="page"]')).toHaveAttribute('href', '/admin/articles')
      await expect(nav.locator('.admin-nav-link[aria-current="page"]')).toHaveCSS('background-color', dark ? 'rgb(34, 53, 82)' : 'rgb(227, 236, 252)')
      if ([390, 1487].includes(width)) {
        await page.screenshot({ path: info.outputPath(`${dark ? 'd' : 'l'}-${width}.png`) })
        expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze()).violations).toEqual([])
      }
      if (mobile) {
        await page.keyboard.press('Escape')
        await expect(page.getByTestId('admin-menu-toggle')).toBeFocused()
        await expect(page.locator('#admin-main')).toHaveJSProperty('inert', false)
        await expect(page.locator('body')).not.toHaveCSS('overflow', 'hidden')
      }
    }
  }
  await page.setViewportSize({ width: 390, height: 844 })
  await page.getByTestId('admin-menu-toggle').click()
  await page.locator('#admin-mobile-drawer').getByRole('link', { name: '读书', exact: true }).click()
  await expect(page).toHaveURL(/\/admin\/books$/)
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(page.locator('#admin-main')).toHaveJSProperty('inert', false)
  await page.getByTestId('admin-menu-toggle').click()
  await page.getByTestId('admin-drawer-backdrop').click({ position: { x: 380, y: 300 } })
  await expect(page.getByTestId('admin-menu-toggle')).toBeFocused()
  await page.getByTestId('admin-menu-toggle').click()
  await page.setViewportSize({ width: 1024, height: 480 })
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(page.locator('body')).not.toHaveCSS('overflow', 'hidden')
  await expect(page.locator('.admin-sidebar').getByRole('button', { name: '退出', exact: true })).toBeInViewport()
  await page.locator('.admin-sidebar').getByRole('link', { name: '问答助手', exact: true }).scrollIntoViewIfNeeded()
  await expect(page.locator('.admin-sidebar').getByRole('link', { name: '问答助手', exact: true })).toBeInViewport()
  // Nested content paths keep the parent navigation item selected.
  await page.goto('/admin/articles/new')
  await expectHydrated(page)
  await expect(page.locator('.admin-sidebar .admin-nav-link[aria-current="page"]')).toHaveAttribute('href', '/admin/articles')
  await page.setViewportSize({ width: 390, height: 844 })
  await page.route('**/api/v1/auth/logout', route => route.fulfill({ status: 503, contentType: 'application/json', body: '{}' }))
  await page.getByTestId('admin-menu-toggle').click()
  await page.locator('#admin-mobile-drawer').getByRole('button', { name: '退出', exact: true }).click()
  await expect(page.getByTestId('logout-error')).toBeVisible()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await page.unroute('**/api/v1/auth/logout')
  await page.getByTestId('admin-menu-toggle').click()
  await page.locator('#admin-mobile-drawer').getByRole('button', { name: '退出', exact: true }).click()
  await expect(page).toHaveURL(/\/admin\/login$/)
  expect(failedIcons).toEqual([])
  // The intentionally injected logout 503 is the only allowed console error.
  expect(errors.filter(message => !message.includes('503'))).toEqual([])
})
