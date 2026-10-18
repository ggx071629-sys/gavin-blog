import { expect, test, type Page } from '@playwright/test'
import { createHash, randomUUID } from 'node:crypto'
import { mkdir, rm, writeFile } from 'node:fs/promises'
import { join, resolve } from 'node:path'
import { expectHydrated } from '../support/hydration'

const captureEnabled = process.env.PENPOT_ALIGNMENT_CAPTURE === '1'
const captureRoot = process.env.PENPOT_ALIGNMENT_CAPTURE_DIR
  ? resolve(process.env.PENPOT_ALIGNMENT_CAPTURE_DIR)
  : resolve(process.cwd(), '..', '..', '.tmp-penpot-alignment-captures')

const viewports = [
  { name: '1440x900', width: 1440, height: 900 },
  { name: '1024x768', width: 1024, height: 768 },
  { name: '414x896', width: 414, height: 896 },
  { name: '390x844', width: 390, height: 844 },
  { name: '320x800', width: 320, height: 800 },
] as const

const themes = ['light', 'dark'] as const
type Theme = typeof themes[number]
type CaptureTarget = 'menu' | 'article' | 'admin'
type CaptureState = 'closed' | 'open' | 'long' | 'short' | 'default' | 'submitting' | 'error'

interface CaptureArtifact {
  file: string
  sha256: string
  viewport: string
  theme: Theme
  target: CaptureTarget
  state: CaptureState
  fullPage: boolean
}

interface CaptureDiagnostic {
  type: 'console' | 'pageerror'
  message: string
  url?: string
}

const setTheme = async (page: Page, theme: typeof themes[number]) => {
  const html = page.locator('html')
  const isDark = await html.evaluate(element => element.classList.contains('dark'))
  if (isDark !== (theme === 'dark')) {
    await page.getByRole('button', { name: '切换颜色主题' })
      .or(page.getByTestId('admin-theme-toggle'))
      .first()
      .click()
  }
  await expect(html).toHaveClass(theme === 'dark' ? /dark/ : /^(?!.*\bdark\b).*$/)
  await page.evaluate(() => document.fonts.ready)
}

const expectNoHorizontalOverflow = async (page: Page, label: string) => {
  const width = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }))
  expect(width.scroll, `${label} horizontal overflow`).toBeLessThanOrEqual(width.client)
}

test('capture the Penpot alignment viewport, theme, and state matrix', async ({ page }) => {
  test.skip(!captureEnabled, 'set PENPOT_ALIGNMENT_CAPTURE=1 to write cross-validation screenshots')
  test.setTimeout(600_000)

  await mkdir(captureRoot, { recursive: true })
  const manifestPath = join(captureRoot, 'manifest.json')
  await rm(manifestPath, { force: true })
  const runId = randomUUID()
  const artifacts: CaptureArtifact[] = []
  const diagnostics: CaptureDiagnostic[] = []
  page.on('pageerror', error => diagnostics.push({ type: 'pageerror', message: error.message }))
  page.on('console', (message) => {
    if (message.type() === 'error') {
      diagnostics.push({ type: 'console', message: message.text(), url: message.location().url || undefined })
    }
  })
  await writeFile(manifestPath, JSON.stringify({ runId, status: 'running' }, null, 2), 'utf8')

  const capture = async (
    name: string,
    metadata: Omit<CaptureArtifact, 'file' | 'sha256'>,
  ) => {
    await expectNoHorizontalOverflow(page, name)
    await page.waitForFunction(() => Array.from(document.images)
      .every(image => image.complete && image.naturalWidth > 0))
    const file = `${name}.png`
    const path = join(captureRoot, file)
    const image = await page.screenshot({ path, fullPage: metadata.fullPage, animations: 'disabled' })
    artifacts.push({
      file,
      sha256: createHash('sha256').update(image).digest('hex'),
      ...metadata,
    })
  }

  await page.goto('/admin/login', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  const csrf = (await page.context().cookies()).find(cookie => cookie.name === 'gavin_csrf')?.value
  expect(csrf).toBeTruthy()
  const headers = { 'X-CSRF-Token': csrf! }

  const categoryResponse = await page.request.post('/api/v1/admin/categories', {
    headers,
    data: { name: '交叉验证', slug: 'penpot-alignment-capture' },
  })
  expect(categoryResponse.status()).toBe(201)
  const category = await categoryResponse.json()
  const tagResponse = await page.request.post('/api/v1/admin/tags', {
    headers,
    data: { name: 'Penpot', slug: 'penpot-alignment-capture' },
  })
  expect(tagResponse.status()).toBe(201)
  const tag = await tagResponse.json()

  const publish = async (title: string, slug: string, content: string, summary: string) => {
    const created = await page.request.post('/api/v1/admin/articles', {
      headers,
      data: {
        title,
        slug,
        summary,
        content,
        category_id: category.id,
        tag_ids: [tag.id],
      },
    })
    expect(created.status(), await created.text()).toBe(201)
    const article = await created.json()
    const published = await page.request.post(`/api/v1/admin/articles/${article.id}/publish`, {
      headers,
      data: { version: article.version },
    })
    expect(published.ok(), await published.text()).toBeTruthy()
    return published.json()
  }

  const shortPrefix = '## 一段短说明\n\n短文章保留真实栏目、标签、摘要与链接，同时把阅读结构压缩到内容所需的最小高度。\n\n'
  const shortContent = `${shortPrefix}${'短文。'.repeat(Math.floor((900 - shortPrefix.length) / 3))}`
  expect(shortContent.length).toBeLessThanOrEqual(1000)
  const longContent = [
    '# 长文章交叉验证',
    '![阅读页题图](/og/gavin-notes-default.png)',
    '这是一篇通过真实发布接口创建的长文章，用于核验日期印章、目录、代码块、Callout 与相关推荐区域。',
    '## 设计映射',
    '正文继续使用 720px 阅读主列，并把证据型代码块控制在 680px。'.repeat(24),
    '```ts capture.ts',
    'const aligned = true',
    '```',
    '::: note',
    '视觉由 Penpot 决定，业务合同由仓库决定。',
    ':::',
    '## 浏览器验证',
    '| Viewport | Theme | State | Evidence |',
    '| --- | --- | --- | --- |',
    '| 1440 | light | long | screenshot |',
    '| 390 | dark | long | screenshot |',
  ].join('\n\n')
  expect(longContent.length).toBeGreaterThan(1000)

  const shortArticle = await publish(
    'Article Short · 真实展示变体',
    'penpot-alignment-short',
    shortContent,
    '两分钟以内、至多一个标题且没有题图时，页面使用紧凑阅读结构。',
  )
  const longArticle = await publish(
    'Article Long · 可诊断阅读路径',
    'penpot-alignment-long',
    longContent,
    '保留日期印章、章节信号、桌面与移动目录的完整长文阅读路径。',
  )

  for (const viewport of viewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height })
    for (const theme of themes) {
      const prefix = `${viewport.name}-${theme}`

      await page.goto('/', { waitUntil: 'domcontentloaded' })
      await expectHydrated(page)
      await setTheme(page, theme)
      await capture(`${prefix}-menu-closed`, {
        viewport: viewport.name,
        theme,
        target: 'menu',
        state: 'closed',
        fullPage: false,
      })
      if (viewport.width < 1280) {
        await page.getByRole('button', { name: '打开主导航菜单' }).click()
        await expect(page.getByTestId('site-menu-overlay')).toBeVisible()
        await capture(`${prefix}-menu-open`, {
          viewport: viewport.name,
          theme,
          target: 'menu',
          state: 'open',
          fullPage: false,
        })
        await page.keyboard.press('Escape')
      }

      await page.goto(longArticle.public_path, { waitUntil: 'domcontentloaded' })
      await expectHydrated(page)
      await setTheme(page, theme)
      await expect(page.locator('.article-reading')).toHaveAttribute('data-article-variant', 'long')
      await capture(`${prefix}-article-long`, {
        viewport: viewport.name,
        theme,
        target: 'article',
        state: 'long',
        fullPage: true,
      })

      await page.goto(shortArticle.public_path, { waitUntil: 'domcontentloaded' })
      await expectHydrated(page)
      await setTheme(page, theme)
      await expect(page.locator('.article-reading')).toHaveAttribute('data-article-variant', 'short')
      await capture(`${prefix}-article-short`, {
        viewport: viewport.name,
        theme,
        target: 'article',
        state: 'short',
        fullPage: true,
      })

      await page.goto('/admin/login', { waitUntil: 'domcontentloaded' })
      await expectHydrated(page)
      await setTheme(page, theme)
      await expect(page.getByTestId('admin-login-shell')).toHaveAttribute('data-state', 'ready')
      await capture(`${prefix}-admin-default`, {
        viewport: viewport.name,
        theme,
        target: 'admin',
        state: 'default',
        fullPage: false,
      })

      let markLoginStarted!: () => void
      let releaseLogin!: () => void
      const loginStarted = new Promise<void>((resolveStarted) => { markLoginStarted = resolveStarted })
      const loginMayFinish = new Promise<void>((resolveLogin) => { releaseLogin = resolveLogin })
      await page.route('**/api/v1/auth/login', async (route) => {
        markLoginStarted()
        await loginMayFinish
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'capture invalid credentials' }),
        })
      })
      await page.getByTestId('password').fill('capture-error')
      await page.getByTestId('login').click()
      await loginStarted
      await expect(page.getByTestId('admin-login-shell')).toHaveAttribute('data-state', 'submitting')
      await expect(page.getByTestId('login')).toBeDisabled()
      await expect(page.getByTestId('login')).toHaveAttribute('aria-busy', 'true')
      await capture(`${prefix}-admin-submitting`, {
        viewport: viewport.name,
        theme,
        target: 'admin',
        state: 'submitting',
        fullPage: false,
      })
      releaseLogin()
      await expect(page.getByRole('alert')).toBeVisible()
      await expect(page.getByTestId('admin-login-shell')).toHaveAttribute('data-state', 'error')
      await expect(page.getByTestId('login')).toBeEnabled()
      await expect(page.getByTestId('login')).toHaveAttribute('aria-busy', 'false')
      await expect(page.getByTestId('login')).toHaveCSS('opacity', '1')
      await page.mouse.move(0, 0)
      await capture(`${prefix}-admin-error`, {
        viewport: viewport.name,
        theme,
        target: 'admin',
        state: 'error',
        fullPage: false,
      })
      await page.unroute('**/api/v1/auth/login')
    }
  }

  const expectedCount = 68
  const uniqueFiles = new Set(artifacts.map(artifact => artifact.file))
  const expectedAuthDiagnostics = diagnostics.filter(diagnostic => diagnostic.type === 'console'
    && diagnostic.url?.endsWith('/api/v1/auth/login')
    && diagnostic.message.includes('401'))
  const unexpectedDiagnostics = diagnostics.filter(diagnostic => !expectedAuthDiagnostics.includes(diagnostic))
  await writeFile(manifestPath, JSON.stringify({
    runId,
    status: unexpectedDiagnostics.length === 0 && artifacts.length === expectedCount ? 'complete' : 'failed',
    generatedAt: new Date().toISOString(),
    penpot: {
      file: 'Gavin_ui_v1',
      fileId: '81f57451-85cc-819d-8008-7c9ef816dd33',
      articleLongPageId: 'faa08c08-ba3b-8031-8008-831742876006',
      articleLongDesktopLight: 'faa08c08-ba3b-8031-8008-83175c70c4d0',
      articleLongMobileLight: 'faa08c08-ba3b-8031-8008-83175caa86f1',
      articleLongDesktopDark: 'faa08c08-ba3b-8031-8008-83175ce2b8b8',
      articleLongMobileDark: 'faa08c08-ba3b-8031-8008-83175eee5988',
      mobileMenu: '153af549-5bcc-80a6-8008-8364c3a8c208',
      articleShortDesktop: 'faa08c08-ba3b-8031-8008-8319492b3c1b',
      articleShortMobile: 'faa08c08-ba3b-8031-8008-83194959df6d',
      adminDesktop: 'faa08c08-ba3b-8031-8008-831cbbe71f65',
      adminMobile: '153af549-5bcc-80a6-8008-836363972a40',
    },
    viewports,
    themes,
    expectedCount,
    actualCount: artifacts.length,
    desktopMenuOpenExcluded: 'At 1440px the canonical desktop navigation replaces the menu trigger.',
    diagnostics: {
      expectedAuthFailures: expectedAuthDiagnostics,
      unexpected: unexpectedDiagnostics,
    },
    artifacts,
  }, null, 2), 'utf8')

  expect(artifacts).toHaveLength(expectedCount)
  expect(uniqueFiles.size).toBe(expectedCount)
  expect(expectedAuthDiagnostics).toHaveLength(viewports.length * themes.length)
  expect(unexpectedDiagnostics, 'unexpected browser console and page errors found during screenshot capture').toEqual([])
})
