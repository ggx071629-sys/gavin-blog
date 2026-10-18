import { expect, test, type Page } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

const setTheme = async (page: Page, theme: 'light' | 'dark') => {
  const html = page.locator('html')
  const isDark = await html.evaluate(element => element.classList.contains('dark'))
  if (isDark !== (theme === 'dark')) {
    await page.getByRole('button', { name: '切换颜色主题' }).first().click()
  }
  await expect(html).toHaveClass(theme === 'dark' ? /dark/ : /^(?!.*\bdark\b).*$/)
}

test('phase 4 indexes and home do not overflow at 390 or 1440', async ({ page }) => {
  test.setTimeout(180_000)
  const routes = ['/', '/books', '/projects', '/archive', '/about']
  for (const width of [390, 1440] as const) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 })
    for (const route of routes) {
      for (const theme of ['light', 'dark'] as const) {
        await page.goto(route, { waitUntil: 'domcontentloaded' })
        await expectHydrated(page)
        await setTheme(page, theme)
        const box = await page.evaluate(() => ({
          client: document.documentElement.clientWidth,
          scroll: document.documentElement.scrollWidth,
        }))
        expect(box.scroll, `${route} ${theme} ${width}`).toBeLessThanOrEqual(box.client)
      }
    }
  }
})

test('home chrome and cards survive phase 4 index restyles', async ({ page }) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await expect(page.getByRole('button', { name: '切换颜色主题' }).first()).toBeVisible()
  await expect(page.getByRole('link', { name: '写作台', exact: true })).toBeVisible()
  await expect(page.locator('.book-grid')).toHaveCount(0)
  await expect(page.locator('.project-grid')).toHaveCount(0)
  await expect(page.locator('.article-list-row')).toHaveCount(0)
})
