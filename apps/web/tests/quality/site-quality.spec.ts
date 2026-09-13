import AxeBuilder from '@axe-core/playwright'
import { chromium, expect, test } from '@playwright/test'
import { launch } from 'chrome-launcher'
import { mkdir, rm } from 'node:fs/promises'
import lighthouse from 'lighthouse'
import desktopConfig from 'lighthouse/core/config/desktop-config.js'
import { expectHydrated as waitForHydration } from '../support/hydration'

let captureSequence = 0

const publicPages = ['/', '/articles', '/books', '/projects', '/archive', '/about', '/search']
const lighthouseCategories = ['performance', 'accessibility', 'best-practices', 'seo'] as const
const homepageVisualMatrix = [
  { name: 'desktop', width: 1440, height: 1100 },
  { name: 'mobile', width: 390, height: 844 },
] as const
const adminLoginVisualMatrix = [
  { name: 'desktop-1440', width: 1440, height: 900 },
  { name: 'desktop-1024', width: 1024, height: 768 },
  { name: 'mobile-414', width: 414, height: 896 },
  { name: 'mobile-390', width: 390, height: 844 },
  { name: 'mobile-320', width: 320, height: 800 },
] as const
const themes = ['light', 'dark'] as const
const runtimeDiagnostics = new WeakMap<import('@playwright/test').Page, string[]>()

test.beforeEach(async ({ page }) => {
  const diagnostics: string[] = []
  runtimeDiagnostics.set(page, diagnostics)
  page.on('console', (message) => {
    if (message.type() === 'warning' || message.type() === 'error') {
      diagnostics.push(`${message.type()}: ${message.text()}`)
    }
  })
  page.on('pageerror', error => diagnostics.push(`pageerror: ${error.message}`))
})

test.afterEach(async ({ page }) => {
  expect(runtimeDiagnostics.get(page) || [], 'browser runtime diagnostics').toEqual([])
})

const expectSecurityHeaders = (headers: Record<string, string>, path: string) => {
  const policy = headers['content-security-policy-report-only'] || ''
  expect(policy, `${path} CSP Report-Only`).toContain("frame-ancestors 'none'")
  expect(policy, `${path} CSP Report-Only`).toContain("object-src 'none'")
  expect(policy, `${path} CSP Report-Only`).toContain("base-uri 'self'")
  expect(policy, `${path} CSP Report-Only`).toContain("form-action 'self'")
  expect(headers['x-frame-options'], path).toBe('DENY')
  expect(headers['x-content-type-options'], path).toBe('nosniff')
  expect(headers['referrer-policy'], path).toBe('strict-origin-when-cross-origin')
  expect(headers['permissions-policy'], path).toBe('camera=(), microphone=(), geolocation=()')
  expect(headers['strict-transport-security'], `${path} local HTTP must not claim HSTS`).toBeUndefined()
}

const loginForQuality = async (page: import('@playwright/test').Page) => {
  await page.goto('/admin/login', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  const csrf = (await page.context().cookies()).find(cookie => cookie.name === 'gavin_csrf')?.value
  expect(csrf).toBeTruthy()
  return csrf!
}

const setTheme = async (page: import('@playwright/test').Page, theme: typeof themes[number]) => {
  await page.evaluate(value => localStorage.setItem('nuxt-color-mode', value), theme)
  await page.reload({ waitUntil: 'networkidle' })
  if (theme === 'dark') await expect(page.locator('html')).toHaveClass(/\bdark\b/)
  else await expect(page.locator('html')).not.toHaveClass(/\bdark\b/)
  await page.evaluate(() => document.fonts.ready)
}

test('production HTML applies security headers to public, missing, login, and admin pages', async ({ page, request }) => {
  for (const path of ['/', '/security-header-missing', '/admin/login']) {
    const response = await request.get(path)
    expectSecurityHeaders(response.headers(), path)
  }

  await loginForQuality(page)
  const adminResponse = await page.goto('/admin/articles', { waitUntil: 'domcontentloaded' })
  expect(adminResponse).not.toBeNull()
  expectSecurityHeaders(adminResponse!.headers(), '/admin/articles')
})

test('media upload reports success, failure, success and retries only the failure', async ({ page }) => {
  await loginForQuality(page)
  let postAttempt = 0
  await page.route('**/api/v1/admin/media', async (route) => {
    if (route.request().method() !== 'POST') {
      await route.fallback()
      return
    }
    postAttempt += 1
    if (postAttempt === 2) {
      await route.fulfill({ status: 422, contentType: 'application/json', body: '{"detail":"injected"}' })
      return
    }
    await route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({
        id: postAttempt,
        source: 'upload',
        original_name: `upload-${postAttempt}.png`,
        alt_text: '',
        mime_type: 'image/webp',
        width: 1,
        height: 1,
        byte_size: 1,
        url: `/api/v1/media/${postAttempt}/webp`,
        variants: [],
        created_at: '2026-08-10T00:00:00Z',
      }),
    })
  })
  await page.goto('/admin/media')
  await waitForHydration(page)
  await page.getByTestId('media-file').setInputFiles([
    { name: 'one.png', mimeType: 'image/png', buffer: Buffer.from('one') },
    { name: 'two.png', mimeType: 'image/png', buffer: Buffer.from('two') },
    { name: 'three.png', mimeType: 'image/png', buffer: Buffer.from('three') },
  ])
  const results = page.getByTestId('media-upload-results').locator('li')
  await expect(results).toHaveCount(3)
  await expect(results.filter({ has: page.getByText('已上传', { exact: true }) })).toHaveCount(2)
  await expect(results.filter({ has: page.getByText('请检查图片格式与大小。') })).toHaveCount(1)
  await page.getByTestId('media-retry-failed').click()
  await expect(results.filter({ has: page.getByText('已上传', { exact: true }) })).toHaveCount(3)
  expect(postAttempt).toBe(4)
  const diagnostics = runtimeDiagnostics.get(page) || []
  const expectedUploadErrors = diagnostics.filter(message => message.includes('status of 422'))
  expect(expectedUploadErrors).toHaveLength(1)
  runtimeDiagnostics.set(page, diagnostics.filter(message => !message.includes('status of 422')))
})

test('production fonts are self-hosted without Google runtime requests', async ({ page, browser }) => {
  const requests: string[] = []
  page.on('request', request => requests.push(request.url()))
  await page.goto('/', { waitUntil: 'networkidle' })
  await page.evaluate(() => document.fonts.ready)
  expect(requests.some(url => url.includes('fonts.googleapis.com'))).toBe(false)
  expect(requests.some(url => url.includes('fonts.gstatic.com'))).toBe(false)
  expect(requests.some(url => url.endsWith('.woff2'))).toBe(true)

  const fallbackContext = await browser.newContext({ viewport: { width: 375, height: 667 } })
  const fallbackPage = await fallbackContext.newPage()
  await fallbackPage.route('**/*.woff2', route => route.abort('failed'))
  await fallbackPage.goto('/', { waitUntil: 'networkidle' })
  await fallbackPage.evaluate(() => document.fonts.ready)
  const fallbackOverflow = await fallbackPage.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }))
  expect(fallbackOverflow.scrollWidth).toBeLessThanOrEqual(fallbackOverflow.clientWidth)
  await fallbackContext.close()
})

const expectNoOverflowOrAxeViolations = async (
  page: import('@playwright/test').Page,
  label: string,
) => {
  const overflow = await page.evaluate(() => {
    const clientWidth = document.documentElement.clientWidth
    return {
      clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
      offenders: Array.from(document.querySelectorAll<HTMLElement>('body *'))
        .map(element => ({ element, rect: element.getBoundingClientRect() }))
        .filter(({ rect }) => rect.right > clientWidth + 1 || rect.left < -1)
        .slice(0, 8)
        .map(({ element, rect }) => ({
          tag: element.tagName.toLowerCase(),
          testId: element.dataset.testid || null,
          className: element.className?.toString().slice(0, 160) || null,
          left: Math.round(rect.left),
          right: Math.round(rect.right),
          width: Math.round(rect.width),
        })),
    }
  })
  expect(overflow.scrollWidth, `${label} horizontal overflow: ${JSON.stringify(overflow.offenders)}`).toBeLessThanOrEqual(overflow.clientWidth)

  await expect.poll(() => page.evaluate(() => document.getAnimations().filter(animation => animation instanceof CSSTransition && animation.playState === 'running').length)).toBe(0)
  const result = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze()
  expect(result.violations.map(violation => ({
    id: violation.id,
    impact: violation.impact,
    targets: violation.nodes.map(node => node.target),
  })), `${label} accessibility violations`).toEqual([])
}

const expectAdminLoginPresentation = async (
  page: import('@playwright/test').Page,
  viewport: typeof adminLoginVisualMatrix[number],
  label: string,
) => {
  const submit = page.getByTestId('login')
  await expect(submit, `${label} hydrated submit`).toBeEnabled()
  await expect(submit, `${label} settled submit transition`).toHaveCSS('opacity', '1')

  const username = page.getByLabel('用户名', { exact: true })
  const password = page.getByLabel('密码', { exact: true })
  const themeToggle = page.getByTestId('admin-theme-toggle')
  await expect(page.getByRole('heading', { level: 1 }), `${label} visible H1`).toHaveCount(1)
  await expect(username, `${label} username label`).toBeVisible()
  await expect(username, `${label} username autocomplete`).toHaveAttribute('autocomplete', 'username')
  await expect(password, `${label} password label`).toBeVisible()
  await expect(password, `${label} password autocomplete`).toHaveAttribute('autocomplete', 'current-password')
  await expect(page.getByRole('link', { name: '返回 Gavin' }), `${label} home link`).toBeVisible()
  await expect(themeToggle, `${label} theme toggle`).toBeVisible()
  await expect(page.locator('meta[name="robots"]'), `${label} robots policy`).toHaveAttribute('content', /^noindex,\s*nofollow$/)
  await expect(page.getByRole('link', { name: /注册|找回密码|忘记密码/ }), `${label} unsupported auth links`).toHaveCount(0)

  await page.evaluate(() => {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur()
  })
  await page.keyboard.press('Tab')
  await expect(themeToggle, `${label} keyboard focus target`).toBeFocused()
  await expect(themeToggle, `${label} visible keyboard focus`).not.toHaveCSS('outline-style', 'none')
  await page.evaluate(() => {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur()
  })

  const presentation = await page.evaluate(() => {
    const read = (testId: string) => {
      const element = document.querySelector<HTMLElement>(`[data-testid="${testId}"]`)
      if (!element) throw new Error(`Missing admin login element: ${testId}`)
      return { rect: element.getBoundingClientRect(), style: getComputedStyle(element) }
    }
    const shell = read('admin-login-shell')
    const stage = read('admin-login-form-stage')
    const surface = read('admin-login-form-surface')
    const roundedRect = (rect: DOMRect) => ({
      left: Math.round(rect.left),
      width: Math.round(rect.width),
    })
    const touchTarget = (name: string, selector: string) => {
      const element = document.querySelector<HTMLElement>(selector)
      if (!element) throw new Error(`Missing admin login target: ${name}`)
      const rect = element.getBoundingClientRect()
      return { height: Math.round(rect.height), name, width: Math.round(rect.width) }
    }

    return {
      shell: roundedRect(shell.rect),
      stage: roundedRect(stage.rect),
      surface: roundedRect(surface.rect),
      surfaceBackgroundColor: surface.style.backgroundColor,
      surfaceBackgroundImage: surface.style.backgroundImage,
      surfaceBorderRadius: surface.style.borderRadius,
      surfaceBorderWidths: [
        surface.style.borderTopWidth,
        surface.style.borderRightWidth,
        surface.style.borderBottomWidth,
        surface.style.borderLeftWidth,
      ],
      surfaceBoxShadow: surface.style.boxShadow,
      touchTargets: [
        touchTarget('theme toggle', '[data-testid="admin-theme-toggle"]'),
        touchTarget('back link', '.admin-login-back'),
        touchTarget('username field', 'label[for="admin-username"]'),
        touchTarget('password field', 'label[for="admin-password"]'),
        touchTarget('submit', '[data-testid="login"]'),
      ],
    }
  })

  expect(presentation.surfaceBackgroundImage, `${label} form surface image`).toBe('none')
  expect(['transparent', 'rgba(0, 0, 0, 0)'], `${label} form surface fill`).toContain(presentation.surfaceBackgroundColor)
  expect(presentation.surfaceBorderWidths, `${label} form surface border`).toEqual(['0px', '0px', '0px', '0px'])
  expect(presentation.surfaceBorderRadius, `${label} form surface radius`).toBe('0px')
  expect(presentation.surfaceBoxShadow, `${label} form surface shadow`).toBe('none')
  for (const target of presentation.touchTargets) {
    expect(target.width, `${label} ${target.name} target width`).toBeGreaterThanOrEqual(44)
    expect(target.height, `${label} ${target.name} target height`).toBeGreaterThanOrEqual(44)
  }

  await expect(page.getByTestId('admin-login-brand-panel')).toHaveCount(0)
  const formWidth = Math.min(430, viewport.width - (viewport.width <= 360 ? 36 : 44))
  expect(presentation.shell, `${label} shell`).toEqual({ left: 0, width: viewport.width })
  expect(presentation.stage, `${label} form stage`).toEqual({ left: 0, width: viewport.width })
  expect(presentation.surface, `${label} centered single-column form`).toEqual({ left: Math.round((viewport.width - formWidth) / 2), width: formWidth })
}

// admin core production pages pass the visual matrix
test('q1', async ({ page }, testInfo) => {
  test.setTimeout(300_000)

  for (const viewport of adminLoginVisualMatrix) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height })
    for (const theme of themes) {
      await page.goto('/admin/login', { waitUntil: 'domcontentloaded' })
      await waitForHydration(page)
      await setTheme(page, theme)
      await waitForHydration(page)
      await expectAdminLoginPresentation(page, viewport, `login ${theme} ${viewport.name}`)
      await expectNoOverflowOrAxeViolations(page, `login ${theme} ${viewport.name}`)
      await page.screenshot({
        path: testInfo.outputPath(`${captureSequence++}.png`),
        fullPage: true,
        animations: 'disabled',
      })
    }
  }

  await page.setViewportSize({ width: 1440, height: 1100 })
  const csrf = await loginForQuality(page)
  const headers = { 'X-CSRF-Token': csrf }
  const fixtures = [
    page.request.post('/api/v1/admin/articles', {
      headers,
      data: { title: '后台视觉验证文章', slug: 'admin-core-visual-article', summary: '验证高密度列表。', content: '# 验证\n\n后台列表固定资料。' },
    }),
    page.request.post('/api/v1/admin/projects', {
      headers,
      data: { title: '后台视觉验证项目', slug: 'admin-core-visual-project', summary: '验证项目列表。', content: '# 验证', repository_url: null, website_url: null, article_ids: [] },
    }),
    page.request.post('/api/v1/admin/books', {
      headers,
      data: { book_title: '后台视觉验证之书', author: '测试作者', slug: 'admin-core-visual-book', cover_url: null, reading_status: 'reading', reading_date: null, rating: null, summary: '验证读书列表。', content: '# 验证' },
    }),
  ]
  const responses = await Promise.all(fixtures)
  for (const response of responses) expect(response.status()).toBe(201)
  const [article, project, book] = await Promise.all(responses.map(response => response.json()))

  const routes = [
    { name: 'articles', path: '/admin/articles', heading: '文章', navPath: '/admin/articles' },
    { name: 'article-new', path: '/admin/articles/new', heading: '新建草稿', navPath: '/admin/articles' },
    { name: 'article-edit', path: `/admin/articles/${article.id}/edit`, heading: '编辑文章', navPath: '/admin/articles' },
    { name: 'article-preview', path: `/admin/articles/${article.id}/preview`, heading: article.title, navPath: '/admin/articles' },
    { name: 'article-revisions', path: `/admin/articles/${article.id}/revisions`, heading: '版本历史', navPath: '/admin/articles' },
    { name: 'projects', path: '/admin/projects', heading: '项目', navPath: '/admin/projects' },
    { name: 'project-new', path: '/admin/projects/new', heading: '新建项目', navPath: '/admin/projects' },
    { name: 'project-edit', path: `/admin/projects/${project.id}/edit`, heading: '编辑项目', navPath: '/admin/projects' },
    { name: 'books', path: '/admin/books', heading: '读书笔记', navPath: '/admin/books' },
    { name: 'book-new', path: '/admin/books/new', heading: '新建读书笔记', navPath: '/admin/books' },
    { name: 'book-edit', path: `/admin/books/${book.id}/edit`, heading: '编辑读书笔记', navPath: '/admin/books' },
    { name: 'profile', path: '/admin/profile', heading: '个人名片', navPath: '/admin/profile' },
    { name: 'about', path: '/admin/about', heading: '关于页内容', navPath: '/admin/about' },
    { name: 'about-preview', path: '/admin/about/preview', heading: /你好，我是/, navPath: '/admin/about' },
    { name: 'about-revisions', path: '/admin/about/revisions', heading: '关于页版本历史', navPath: '/admin/about' },
    { name: 'taxonomy', path: '/admin/taxonomy', heading: '栏目与标签', navPath: '/admin/taxonomy' },
    { name: 'media', path: '/admin/media', heading: '媒体库', navPath: '/admin/media' },
    { name: 'content', path: '/admin/content', heading: '回收站与迁移', navPath: '/admin/content' },
    { name: 'assistant', path: '/admin/assistant', heading: '问答助手管理', navPath: '/admin/assistant' },
  ]

  for (const viewport of homepageVisualMatrix) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height })
    for (const theme of themes) {
      for (const route of routes) {
        await page.goto(route.path, { waitUntil: 'networkidle' })
        await setTheme(page, theme)
        await expect(page.getByRole('heading', { level: 1, name: route.heading })).toBeVisible()
        if (route.navPath) {
          await expect(page.locator('.admin-sidebar .admin-core-nav a[aria-current="page"]')).toHaveAttribute('href', route.navPath)
        }
        await expectNoOverflowOrAxeViolations(page, `${route.name} ${theme} ${viewport.name}`)
        await page.screenshot({
          path: testInfo.outputPath(`${captureSequence++}.png`),
          fullPage: true,
          animations: 'disabled',
        })
      }
    }
  }

})

// mobile admin drawer traps focus and skill actions meet touch targets
test('q2', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await loginForQuality(page)
  await page.goto('/admin/articles', { waitUntil: 'networkidle' })
  const menuButton = page.getByTestId('admin-menu-toggle')
  await menuButton.click()
  await expect(menuButton).toHaveAttribute('aria-expanded', 'true')
  const drawer = page.locator('#admin-mobile-drawer')
  await expect(drawer).toBeVisible()
  await expect(drawer).toHaveAttribute('role', 'dialog')
  await expect(drawer).toHaveAttribute('aria-modal', 'true')
  const firstDrawerControl = drawer.locator('button').first()
  const lastDrawerControl = drawer.locator('button').last()
  await expect(firstDrawerControl).toBeFocused()
  await expect(page.locator('#admin-main')).toHaveJSProperty('inert', true)
  await page.keyboard.press('Shift+Tab')
  await expect(lastDrawerControl).toBeFocused()
  await page.keyboard.press('Tab')
  await expect(firstDrawerControl).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(drawer).toBeHidden()
  await expect(menuButton).toBeFocused()
  await expect(page.locator('#admin-main')).toHaveJSProperty('inert', false)

  await menuButton.click()
  await page.getByTestId('admin-drawer-backdrop').click({ position: { x: 385, y: 800 } })
  await expect(drawer).toBeHidden()
  await expect(menuButton).toBeFocused()

  await menuButton.click()
  await drawer.locator('a[href="/admin/projects"]').click()
  await expect(page).toHaveURL(/\/admin\/projects$/)
  await expect(drawer).toBeHidden()
  await expect(page.locator('#admin-main')).toHaveJSProperty('inert', false)

  for (const viewport of [{ width: 375, height: 667 }, { width: 740, height: 390 }]) {
    await page.setViewportSize(viewport)
    await page.goto('/admin/articles', { waitUntil: 'networkidle' })
    if (viewport.width === 375) {
      await page.evaluate(() => { document.documentElement.style.fontSize = '200%' })
    }
    const viewportMenuButton = page.getByTestId('admin-menu-toggle')
    await viewportMenuButton.click()
    const viewportDrawer = page.locator('#admin-mobile-drawer')
    const viewportFirst = viewportDrawer.locator('button').first()
    const viewportLast = viewportDrawer.locator('button').last()
    await expect(viewportFirst).toBeFocused()
    await page.keyboard.press('Shift+Tab')
    await expect(viewportLast).toBeFocused()
    await expect(viewportFirst).toBeVisible()
    await expect(viewportLast).toBeVisible()
    const overflow = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }))
    expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth)
    await page.keyboard.press('Escape')
    await expect(viewportMenuButton).toBeFocused()
  }

  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/admin/articles', { waitUntil: 'networkidle' })
  await page.getByTestId('admin-menu-toggle').click()
  await page.setViewportSize({ width: 1200, height: 800 })
  await expect(page.locator('#admin-mobile-drawer')).toBeHidden()
  await expect(page.locator('#admin-main')).toHaveJSProperty('inert', false)
  await expect.poll(() => page.evaluate(() => document.body.style.overflow)).toBe('')

  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/admin/profile', { waitUntil: 'networkidle' })
  const skillInput = page.getByTestId('profile-skill-input')
  await skillInput.fill('Accessibility')
  await page.getByTestId('profile-skill-add').click()
  for (const testId of ['profile-skill-up-0', 'profile-skill-down-0', 'profile-skill-remove-0']) {
    const box = await page.getByTestId(testId).boundingBox()
    expect(box?.width, `${testId} width`).toBeGreaterThanOrEqual(44)
    expect(box?.height, `${testId} height`).toBeGreaterThanOrEqual(44)
  }
})

// homepage captures accessible light and dark desktop and mobile evidence
test('q4', async ({ page }, testInfo) => {
  await page.goto('/admin/login', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  const csrf = (await page.context().cookies()).find(cookie => cookie.name === 'gavin_csrf')?.value
  expect(csrf).toBeTruthy()
  const currentProfileResponse = await page.request.get('/api/v1/admin/profile')
  expect(currentProfileResponse.ok()).toBeTruthy()
  const currentProfile = await currentProfileResponse.json()
  const updatedProfileResponse = await page.request.patch('/api/v1/admin/profile', {
    headers: { 'X-CSRF-Token': csrf! },
    data: {
      name: currentProfile.name,
      title: currentProfile.title,
      bio: currentProfile.bio,
      skills: currentProfile.skills,
      avatar_url: currentProfile.avatar_url,
      city: currentProfile.city,
      city_visible: currentProfile.city_visible,
      github_url: 'https://github.com/gavinhub',
      website_url: 'https://gavinhub.example.com',
      email: 'gavin@example.com',
      email_visible: true,
      resume_url: 'https://gavinhub.example.com/resume.pdf',
      version: currentProfile.version,
    },
  })
  expect(updatedProfileResponse.ok()).toBeTruthy()
  const samples = [
    ['Nuxt 3 性能优化实践', '从首屏加载到交互响应，记录可复验的渲染性能优化路径。'],
    ['复杂 API 设计的权衡', '在稳定契约、演进成本与调用效率之间寻找可维护的边界。'],
    ['2026 年度工程复盘', '回顾有效的工程决策，也记录应该更早暴露的风险。'],
    ['AI 辅助编程工作流建立', '把模型能力纳入可检查、可回退的日常开发循环。'],
  ] as const
  for (const [index, sample] of samples.entries()) {
    const created = await page.request.post('/api/v1/admin/articles', {
      headers: { 'X-CSRF-Token': csrf! },
      data: {
        title: sample[0],
        slug: `homepage-visual-${index}`,
        summary: sample[1],
        content: `# ${sample[0]}\n\n${sample[1]}\n\n这是用于第一阶段视觉验证的隔离测试内容。`,
      },
    })
    expect(created.status()).toBe(201)
    const article = await created.json()
    const published = await page.request.post(`/api/v1/admin/articles/${article.id}/publish`, {
      headers: { 'X-CSRF-Token': csrf! },
      data: { version: article.version },
    })
    expect(published.ok()).toBeTruthy()
  }

  for (const viewport of homepageVisualMatrix) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height })
    for (const theme of themes) {
      await page.goto('/', { waitUntil: 'domcontentloaded' })
      await page.evaluate((value) => localStorage.setItem('nuxt-color-mode', value), theme)
      await page.reload({ waitUntil: 'networkidle' })
      await waitForHydration(page)
      if (theme === 'dark') {
        await expect(page.locator('html')).toHaveClass(/\bdark\b/)
      }
      else {
        await expect(page.locator('html')).not.toHaveClass(/\bdark\b/)
      }

      await page.evaluate(() => document.fonts.ready)
      const overflow = await page.evaluate(() => ({
        clientWidth: document.documentElement.clientWidth,
        scrollWidth: document.documentElement.scrollWidth,
      }))
      expect(overflow.scrollWidth, `${theme} ${viewport.name} horizontal overflow`).toBeLessThanOrEqual(overflow.clientWidth)

      const result = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze()
      const summary = result.violations.map(violation => ({
        id: violation.id,
        impact: violation.impact,
        help: violation.help,
        targets: violation.nodes.map(node => node.target),
      }))
      expect(summary, `${theme} ${viewport.name} accessibility violations`).toEqual([])

      await page.screenshot({
        path: testInfo.outputPath(`${captureSequence++}.png`),
        fullPage: true,
        animations: 'disabled',
      })
    }
  }
})

// public page families capture light and dark desktop and mobile evidence
test('q5', async ({ page }, testInfo) => {
  test.setTimeout(300_000)
  const csrf = await loginForQuality(page)
  const headers = { 'X-CSRF-Token': csrf }
  const projectPaths: string[] = []
  const bookPaths: string[] = []
  const articleResponse = await page.request.post('/api/v1/admin/articles', {
    headers,
    data: {
      title: '公开页面矩阵文章',
      slug: 'public-visual-article',
      summary: '为独立运行的公开详情矩阵提供确定性文章。',
      content: '# 公开页面矩阵文章\n\n不依赖其他测试创建的数据。',
    },
  })
  expect(articleResponse.status()).toBe(201)
  const article = await articleResponse.json()
  const publishedArticle = await page.request.post(`/api/v1/admin/articles/${article.id}/publish`, {
    headers,
    data: { version: article.version },
  })
  expect(publishedArticle.ok()).toBeTruthy()
  const articlePath = (await publishedArticle.json()).public_path as string

  for (let index = 0; index < 3; index += 1) {
    const projectResponse = await page.request.post('/api/v1/admin/projects', {
      headers,
      data: {
        title: ['可回退的内容发布管线', '知识检索工作台', '可观测性仪表盘'][index],
        slug: `public-visual-project-${index}`,
        summary: '从约束、失败路径和可验证结果出发，记录一项持续演进的工程实践。',
        content: '## 背景与挑战\n\n系统需要在不破坏公开契约的前提下完成演进。\n\n## 技术决策\n\n选择可回退、可测试并且边界清晰的实现路径。\n\n```ts\nexport const verified = true\n```',
        repository_url: index === 0 ? 'https://github.com/example/editorial-pipeline' : null,
        website_url: null,
        article_ids: [],
      },
    })
    expect(projectResponse.status()).toBe(201)
    const project = await projectResponse.json()
    const published = await page.request.post(`/api/v1/admin/projects/${project.id}/publish`, {
      headers,
      data: { version: project.version },
    })
    expect(published.ok()).toBeTruthy()
    projectPaths.push((await published.json()).public_path)

    const bookResponse = await page.request.post('/api/v1/admin/books', {
      headers,
      data: {
        book_title: ['Designing Data-Intensive Applications', 'A Philosophy of Software Design', 'Staff Engineer'][index],
        author: ['Martin Kleppmann', 'John Ousterhout', 'Will Larson'][index],
        slug: `public-visual-book-${index}`,
        cover_url: null,
        reading_status: index === 1 ? 'reading' : 'completed',
        reading_date: '2026-08-08',
        rating: 5 - index,
        summary: '记录这本书改变工程判断的核心观点，以及可以立即执行的实践。',
        content: '## 核心观点\n\n复杂度必须被持续管理，而不是被抽象层暂时隐藏。\n\n### 行动清单\n\n- 明确约束\n- 保留验证证据',
      },
    })
    expect(bookResponse.status()).toBe(201)
    const book = await bookResponse.json()
    const publishedBook = await page.request.post(`/api/v1/admin/books/${book.id}/publish`, {
      headers,
      data: { version: book.version },
    })
    expect(publishedBook.ok()).toBeTruthy()
    bookPaths.push((await publishedBook.json()).public_path)
  }

  const routes = [
    { name: 'articles', path: '/articles' },
    { name: 'article-detail', path: articlePath },
    { name: 'projects', path: '/projects' },
    { name: 'project-detail', path: projectPaths[0]! },
    { name: 'books', path: '/books' },
    { name: 'book-detail', path: bookPaths[0]! },
    { name: 'archive', path: '/archive' },
    { name: 'about', path: '/about' },
    { name: 'search', path: '/search?q=Nuxt' },
    { name: 'not-found', path: '/public-visual-missing' },
  ]

  for (const route of routes) {
    await page.goto(route.path, { waitUntil: 'networkidle' })
    if (route.name.endsWith('detail')) {
      await expect(page.getByRole('heading', { level: 1 })).toHaveCount(1)
    }
    const axeResult = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze()
    expect(axeResult.violations.map(violation => ({
      id: violation.id,
      targets: violation.nodes.map(node => node.target),
    })), `${route.name} accessibility violations`).toEqual([])

    for (const viewport of homepageVisualMatrix) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height })
      for (const theme of themes) {
        await page.goto(route.path, { waitUntil: 'domcontentloaded' })
        await setTheme(page, theme)
        const overflow = await page.evaluate(() => ({
          clientWidth: document.documentElement.clientWidth,
          scrollWidth: document.documentElement.scrollWidth,
        }))
        expect(overflow.scrollWidth, `${route.name} ${theme} ${viewport.name} horizontal overflow`).toBeLessThanOrEqual(overflow.clientWidth)
        await page.screenshot({
          path: testInfo.outputPath(`${captureSequence++}.png`),
          fullPage: true,
          animations: 'disabled',
        })
      }
    }
  }
  const diagnostics = runtimeDiagnostics.get(page) || []
  const expectedNotFound = diagnostics.filter(message => message.includes('404 (Page not found: /public-visual-missing)'))
  expect(expectedNotFound.length).toBeGreaterThan(0)
  runtimeDiagnostics.set(
    page,
    diagnostics.filter(message => !message.includes('404 (Page not found: /public-visual-missing)')),
  )
})

test('public pages have no automated WCAG A or AA violations', async ({ page }) => {
  for (const path of publicPages) {
    await page.goto(path, { waitUntil: 'networkidle' })
    await waitForHydration(page)
    const result = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze()
    const summary = result.violations.map(violation => ({
      id: violation.id,
      impact: violation.impact,
      help: violation.help,
      targets: violation.nodes.map(node => node.target),
    }))
    expect(summary, `${path} accessibility violations`).toEqual([])
  }
})

test.describe('lighthouse', () => {
  test.describe.configure({ retries: 1 })

  // eslint-disable-next-line no-empty-pattern -- Playwright requires an object destructuring fixtures slot
  test('local production-build preview homepage meets all Lighthouse 90 thresholds', async ({}, testInfo) => {
    const userDataDir = testInfo.outputPath('lighthouse-profile')
    await mkdir(userDataDir, { recursive: true })
    const chrome = await launch({
      chromePath: chromium.executablePath(),
      chromeFlags: ['--headless=new', '--no-sandbox', '--disable-gpu'],
      handleSIGINT: false,
      userDataDir,
    })

    try {
      const result = await lighthouse('http://127.0.0.1:3300/', {
        port: chrome.port,
        logLevel: 'error',
        output: 'json',
        onlyCategories: [...lighthouseCategories],
      }, desktopConfig)
      expect(result, 'Lighthouse returned no result').toBeTruthy()
      const scores = Object.fromEntries(lighthouseCategories.map((category) => {
        const score = result!.lhr.categories[category]?.score || 0
        return [category, Math.round(score * 100)]
      }))
      console.log('Lighthouse scores:', scores)
      for (const category of lighthouseCategories) {
        expect(scores[category], `${category} score`).toBeGreaterThanOrEqual(90)
      }
    }
    finally {
      const processExit = chrome.process && chrome.process.exitCode === null
        ? new Promise<void>((resolve, reject) => {
            const timer = setTimeout(() => reject(new Error('Chromium did not exit after Browser.close')), 15_000)
            chrome.process!.once('exit', () => {
              clearTimeout(timer)
              resolve()
            })
          })
        : Promise.resolve()
      const browser = await chromium.connectOverCDP(`http://127.0.0.1:${chrome.port}`)
      const session = await browser.newBrowserCDPSession()
      await session.send('Browser.close').catch(() => undefined)
      await processExit
      await browser.close().catch(() => undefined)
      await rm(userDataDir, {
        recursive: true,
        force: true,
        maxRetries: 10,
        retryDelay: 200,
      })
    }
  })
})
