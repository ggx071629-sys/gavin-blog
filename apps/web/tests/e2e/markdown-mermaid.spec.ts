import { expect, test } from '@playwright/test'
import { expectHydrated as waitForHydration } from '../support/hydration'

test('Mermaid redraws for the resolved theme and invalid diagrams degrade locally', async ({ page, context }) => {
  const diagnostics: string[] = []
  page.on('pageerror', error => diagnostics.push(`pageerror: ${error.message}`))
  page.on('console', (message) => {
    if (message.type() !== 'error') return
    // Isolated worktrees on another drive 404 Vite @fs font files; production serves them from the build.
    if (/Failed to load resource: the server responded with a status of 404 \(Not Found\)/.test(message.text())) return
    diagnostics.push(`console: ${message.text()}`)
  })
  page.on('response', (response) => {
    if (response.status() !== 404) return
    if (/\/@fontsource\/.+\.(woff2?|ttf)(\?|$)/i.test(response.url())) return
    diagnostics.push(`404: ${response.url()}`)
  })

  await page.goto('/admin/login', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  const csrf = (await context.cookies()).find(cookie => cookie.name === 'gavin_csrf')?.value
  expect(csrf).toBeTruthy()

  const created = await page.request.post('/api/v1/admin/articles', {
    headers: { 'X-CSRF-Token': csrf! },
    data: {
      title: 'Mermaid 主题与降级',
      slug: 'mermaid-theme-fallback',
      summary: '验证 Mermaid 主题重绘与局部错误降级。',
      content: [
        '# Mermaid 主题与降级',
        '',
        'Stable prose marker.',
        '',
        'Inline math: $E = mc^2$.',
        '',
        '```mermaid',
        'graph TD',
        '  A[Light] --> B[Dark]',
        '```',
        '',
        '```mermaid',
        'graph TD',
        '  A[',
        '```',
      ].join('\n'),
    },
  })
  expect(created.status()).toBe(201)
  const article = await created.json()
  const published = await page.request.post(`/api/v1/admin/articles/${article.id}/publish`, {
    headers: { 'X-CSRF-Token': csrf! },
    data: { version: article.version },
  })
  expect(published.ok()).toBeTruthy()
  const publishedArticle = await published.json()
  const publishedAt = new Date(publishedArticle.published_at)
  const path = `/notes/${publishedAt.getUTCFullYear()}/${String(publishedAt.getUTCMonth() + 1).padStart(2, '0')}/mermaid-theme-fallback`

  await page.setViewportSize({ width: 1440, height: 900 })
  await page.evaluate(() => localStorage.setItem('nuxt-color-mode', 'light'))
  await page.goto(path, { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  await expect(page.locator('html')).not.toHaveClass(/dark/)
  await expect(page.locator('.katex')).toContainText('E', { timeout: 30_000 })
  await expect(page.locator('.katex')).toHaveCSS('font-family', /KaTeX_Main/)
  await expect(page.locator('.katex-mathml annotation')).toHaveText('E = mc^2')
  const diagrams = page.locator('[data-mermaid-block]')
  await expect(diagrams).toHaveCount(2)
  const valid = diagrams.nth(0)
  const invalid = diagrams.nth(1)
  await expect(valid).toHaveAttribute('data-mermaid-state', 'ready', { timeout: 30_000 })
  await expect(invalid).toHaveAttribute('data-mermaid-state', 'ready')
  await expect(valid.locator('svg')).toBeVisible()
  await expect(valid).toHaveAttribute('data-mermaid-theme', 'default')
  await expect(invalid).toHaveClass(/mermaid-error/)
  await expect(invalid.getByRole('alert')).toContainText('已保留 Mermaid 源码')
  await expect(invalid.locator('code')).toContainText('A[')
  await expect(invalid.getByRole('button', { name: '复制 Mermaid 源码' })).toBeVisible()

  await context.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: new URL(page.url()).origin })
  await invalid.getByRole('button', { name: '复制 Mermaid 源码' }).click()
  await expect(invalid.locator('[data-mermaid-copy-status]')).toHaveText('Mermaid 源码已复制。')
  expect(await page.evaluate(() => navigator.clipboard.readText())).toContain('A[')

  const prose = await page.getByText('Stable prose marker.').elementHandle()
  expect(prose).not.toBeNull()
  const lightSvg = await valid.locator('svg').innerHTML()
  await page.getByRole('button', { name: '切换颜色主题' }).first().click()
  await expect(page.locator('html')).toHaveClass(/dark/)
  await expect(valid).toHaveAttribute('data-mermaid-state', 'ready', { timeout: 30_000 })
  await expect(valid).toHaveAttribute('data-mermaid-theme', 'dark')
  await expect(valid.locator('svg')).toBeVisible()
  expect(await valid.locator('svg').innerHTML()).not.toBe(lightSvg)
  expect(await prose!.evaluate(element => element.isConnected)).toBe(true)
  await expect(invalid.getByRole('alert')).toBeVisible()
  expect(diagnostics).toEqual([])
})
