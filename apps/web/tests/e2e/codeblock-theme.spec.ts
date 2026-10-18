import { expect, test, type Page } from '@playwright/test'
import { expectHydrated as waitForHydration } from '../support/hydration'

const setTheme = async (page: Page, theme: 'light' | 'dark') => {
  const html = page.locator('html')
  const isDark = await html.evaluate(element => element.classList.contains('dark'))

  if (isDark !== (theme === 'dark')) {
    await page.getByRole('button', { name: '切换颜色主题' })
      .or(page.getByTestId('admin-theme-toggle'))
      .filter({ visible: true })
      .first()
      .click()
  }

  await expect(html).toHaveClass(theme === 'dark' ? /dark/ : /^(?!.*\bdark\b).*$/)
  await page.evaluate(() => document.fonts.ready)
  await page.evaluate(async () => {
    await new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))
  })
  await expect.poll(() => page.evaluate(() => document.getAnimations().filter(animation => animation instanceof CSSTransition && animation.playState === 'running').length)).toBe(0)
}

const parseColor = (color: string): [number, number, number] => {
  const match = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/)
  return match ? [Number(match[1]), Number(match[2]), Number(match[3])] : [0, 0, 0]
}

const luminance = (rgb: [number, number, number]): number => {
  const channel = (value: number) => {
    const s = value / 255
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
  }
  return 0.2126 * channel(rgb[0]) + 0.7152 * channel(rgb[1]) + 0.0722 * channel(rgb[2])
}

const contrastRatio = (color1: string, color2: string): number => {
  const l1 = luminance(parseColor(color1))
  const l2 = luminance(parseColor(color2))
  return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05)
}

const codeblockContent = [
  '# 代码块主题验证',
  '',
  '有语言代码块：',
  '',
  '```js',
  'const answer = 42;',
  '```',
  '',
  '无语言代码块：',
  '',
  '```',
  'plain text without language',
  '```',
  '',
  'language-text 代码块：',
  '',
  '```text',
  'cd /path/to/project',
  '```',
  '',
].join('\n')

const readCodeblockStyles = (page: Page) => page.evaluate(() => {
  const pres = Array.from(document.querySelectorAll<HTMLPreElement>('article.prose-gavin pre'))
  if (!pres.length) throw new Error('Missing pre elements in article body')
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = 1
  const context = canvas.getContext('2d')!
  // CSS color-mix may serialize as color(srgb ...), not rgb(...).
  const rgb = (color: string) => {
    context.clearRect(0, 0, 1, 1)
    context.fillStyle = color
    context.fillRect(0, 0, 1, 1)
    const [r, g, b, alpha] = context.getImageData(0, 0, 1, 1).data
    if (alpha !== 255) throw new Error(`Expected opaque code color: ${color}`)
    return `rgb(${r}, ${g}, ${b})`
  }

  return pres.map((pre) => {
    const preStyle = getComputedStyle(pre)
    const surface = pre.closest<HTMLElement>('.article-code')
    if (!surface) throw new Error('Missing visible code surface')
    const keyword = pre.querySelector<HTMLElement>('.hljs-keyword')
    const stringToken = pre.querySelector<HTMLElement>('.hljs-string')
    return {
      preColor: rgb(preStyle.color),
      preBackground: rgb(getComputedStyle(surface).backgroundColor),
      keywordColor: keyword ? rgb(getComputedStyle(keyword).color) : null,
      stringColor: stringToken ? rgb(getComputedStyle(stringToken).color) : null,
      tokenColors: Array.from(pre.querySelectorAll<HTMLElement>('[class*="hljs-"]'))
        .map(token => rgb(getComputedStyle(token).color)),
      hasTokens: pre.querySelector('.hljs-keyword') !== null,
    }
  })
})

test('codeblocks keep readable syntax and switch surfaces in both color modes', async ({ page }) => {
  test.setTimeout(180_000)
  await page.setViewportSize({ width: 1280, height: 900 })

  await page.goto('/admin/login', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)

  const csrf = (await page.context().cookies()).find(cookie => cookie.name === 'gavin_csrf')?.value
  expect(csrf).toBeTruthy()

  const created = await page.request.post('/api/v1/admin/articles', {
    headers: { 'X-CSRF-Token': csrf! },
    data: {
      title: '代码块主题验证',
      slug: 'codeblock-theme-verify',
      summary: '验证浅色与深色模式代码块可见性。',
      content: codeblockContent,
    },
  })
  expect(created.status()).toBe(201)
  const article = await created.json()

  await page.goto(`/admin/articles/${article.id}/preview`, { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)

  await setTheme(page, 'light')
  const lightBlocks = await readCodeblockStyles(page)
  expect(lightBlocks.length).toBeGreaterThanOrEqual(3)

  for (const [index, block] of lightBlocks.entries()) {
    const ratio = contrastRatio(block.preColor, block.preBackground)
    expect(ratio, `light pre ${index} contrast ${ratio}`).toBeGreaterThanOrEqual(4.5)
    expect(block.preColor, `light pre ${index} color equals background`).not.toBe(block.preBackground)
    for (const color of block.tokenColors) expect(contrastRatio(color, block.preBackground), `light syntax ${index}`).toBeGreaterThanOrEqual(4.5)
  }

  expect(lightBlocks.some(block => block.hasTokens)).toBe(true)

  await setTheme(page, 'dark')
  const darkBlocks = await readCodeblockStyles(page)

  for (const [index, block] of darkBlocks.entries()) {
    const ratio = contrastRatio(block.preColor, block.preBackground)
    expect(ratio, `dark pre ${index} contrast ${ratio}`).toBeGreaterThanOrEqual(4.5)
    expect(block.preColor, `dark pre ${index} color equals background`).not.toBe(block.preBackground)
    for (const color of block.tokenColors) expect(contrastRatio(color, block.preBackground), `dark syntax ${index}`).toBeGreaterThanOrEqual(4.5)
  }

  expect(darkBlocks.some(block => block.hasTokens)).toBe(true)
  expect(darkBlocks).toHaveLength(lightBlocks.length)
  for (const [index, block] of darkBlocks.entries()) {
    expect(block.preBackground, `code surface ${index} follows theme`).not.toBe(lightBlocks[index]!.preBackground)
  }
})
