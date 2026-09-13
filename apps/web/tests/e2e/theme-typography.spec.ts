import { expect, test } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

const viewports = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
] as const

for (const viewport of viewports) {
  test(`${viewport.name} keeps heading typography stable across theme changes`, async ({ page }) => {
    await page.setViewportSize(viewport)
    await page.emulateMedia({ colorScheme: 'light' })
    await page.goto('/about', { waitUntil: 'domcontentloaded' })
    await expectHydrated(page)
    await expect(page.locator('html')).not.toHaveClass(/dark/)

    const brand = page.getByRole('link', { name: 'Gavin 首页' })
    await expect(brand).toBeVisible()
    const chineseHeading = page.getByRole('heading', { level: 1 }).first()
    await expect(chineseHeading).toBeVisible()

    const readTypography = (locator: ReturnType<typeof page.getByRole>) => locator.evaluate((element) => {
      const range = document.createRange()
      range.selectNodeContents(element)
      return {
        fontFamily: getComputedStyle(element).fontFamily,
        glyphWidth: range.getBoundingClientRect().width,
      }
    })

    const light = await readTypography(brand)
    const lightChinese = await readTypography(chineseHeading)
    await page.getByRole('button', { name: '切换颜色主题' }).click()
    await expect(page.locator('html')).toHaveClass(/dark/)
    const dark = await readTypography(brand)
    const darkChinese = await readTypography(chineseHeading)

    expect(light.fontFamily).toContain('Inter')
    expect(light.fontFamily).not.toContain('Hanken')
    expect(lightChinese.fontFamily).toContain('Noto Sans SC')
    expect(dark.fontFamily).toBe(light.fontFamily)
    expect(dark.glyphWidth).toBe(light.glyphWidth)
    expect(darkChinese.fontFamily).toBe(lightChinese.fontFamily)

    const overflow = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }))
    expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth)
  })
}
