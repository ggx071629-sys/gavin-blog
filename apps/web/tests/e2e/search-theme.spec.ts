import { expect, test, type Page } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

type SearchLayout = {
  stage: {
    alignItems: string
    display: string
    justifyContent: string
  }
  panel: {
    borderWidth: string
    maxWidth: string
    padding: string
    width: number
  }
}

const setTheme = async (page: Page, theme: 'light' | 'dark') => {
  const html = page.locator('html')
  const isDark = await html.evaluate(element => element.classList.contains('dark'))

  if (isDark !== (theme === 'dark')) {
    await page.getByRole('button', { name: '切换颜色主题' }).click()
  }

  await expect(html).toHaveClass(theme === 'dark' ? /dark/ : /^(?!.*\bdark\b).*$/)
}

const readSearchLayout = (page: Page) => page.evaluate<SearchLayout>(() => {
  const stage = document.querySelector<HTMLElement>('.search-stage')
  const panel = document.querySelector<HTMLElement>('.search-panel')

  if (!stage || !panel) {
    throw new Error('Search layout is missing')
  }

  const stageStyle = getComputedStyle(stage)
  const panelStyle = getComputedStyle(panel)
  const panelRect = panel.getBoundingClientRect()
  const transparent = (value: string) => value === 'transparent' || value === 'rgba(0, 0, 0, 0)'

  return {
    stage: {
      alignItems: stageStyle.alignItems,
      display: stageStyle.display,
      justifyContent: stageStyle.justifyContent,
    },
    panel: {
      borderWidth: transparent(panelStyle.borderTopColor) ? '0px' : panelStyle.borderTopWidth,
      maxWidth: panelStyle.maxWidth,
      padding: panelStyle.padding,
      width: panelRect.width,
    },
  }
})

const overflowAt = async (page: Page, width: number) => {
  await page.setViewportSize({ width, height: 900 })
  await page.goto('/search', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  const box = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }))
  expect(box.scroll, `${width}px overflow`).toBeLessThanOrEqual(box.client)
}

test('desktop search uses the same full-page layout in light and dark themes', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 })
  await page.goto('/search', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)

  await expect(page.getByRole('link', { name: '写作台', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: '关闭' })).toBeVisible()
  await expect(page.getByTestId('search-idle')).toHaveText('输入关键词开始搜索全部已发布内容。')
  await expect(page.getByTestId('search-chips').locator('a, button')).toHaveCount(0)

  await setTheme(page, 'light')
  const light = await readSearchLayout(page)

  await setTheme(page, 'dark')
  const dark = await readSearchLayout(page)

  expect(light.stage.justifyContent).not.toBe('center')
  expect(light.panel.maxWidth).not.toBe('896px')
  expect(light.panel.width).toBe(900)
  expect(Number.parseFloat(light.panel.borderWidth)).toBe(0)
  expect(light).toEqual(dark)

  await page.getByRole('link', { name: '关闭' }).click()
  await expect(page).toHaveURL(/\/$/)
})

test('mobile search keeps a full-page layout without a centered card or overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/search', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)

  await setTheme(page, 'light')
  const light = await readSearchLayout(page)
  await setTheme(page, 'dark')
  const dark = await readSearchLayout(page)

  expect(light.panel.maxWidth).not.toBe('896px')
  expect(Number.parseFloat(light.panel.borderWidth)).toBe(0)
  expect(light).toEqual(dark)
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
  await expect(page.getByRole('button', { name: '打开主导航菜单' })).toBeVisible()
})

test('1024 keeps desktop search content with mobile chrome, 1280 uses desktop nav', async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 800 })
  await page.goto('/search', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  const availableWidth = await page.locator('.search-stage').evaluate((element) => {
    const style = getComputedStyle(element)
    return element.getBoundingClientRect().width - Number.parseFloat(style.paddingLeft) - Number.parseFloat(style.paddingRight)
  })
  const layout = await readSearchLayout(page)
  expect(layout.panel.maxWidth).not.toBe('896px')
  expect(layout.panel.maxWidth).toBe('900px')
  expect(layout.panel.width).toBe(Math.min(900, availableWidth))
  await expect(page.getByRole('button', { name: '打开主导航菜单' })).toBeVisible()

  await page.setViewportSize({ width: 1280, height: 800 })
  await expect(page.getByRole('button', { name: '打开主导航菜单' })).toHaveCount(0)
  await expect(page.getByRole('link', { name: '写作台', exact: true })).toBeVisible()
})

test('search does not overflow at regression viewports', async ({ page }) => {
  for (const width of [390, 768, 1024, 1280, 1440]) {
    await overflowAt(page, width)
  }
})

