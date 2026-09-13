import { expect, test } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

const unavailablePages = [
  '/',
  '/articles',
  '/projects',
  '/books',
  '/archive',
  '/about',
  '/search?q=failure',
]

const expectSecurityHeaders = (headers: Record<string, string>, path: string) => {
  const policy = headers['content-security-policy-report-only'] || ''
  expect(policy, `${path} CSP Report-Only`).toContain("frame-ancestors 'none'")
  expect(policy, `${path} CSP Report-Only`).toContain("object-src 'none'")
  expect(headers['x-frame-options'], path).toBe('DENY')
  expect(headers['x-content-type-options'], path).toBe('nosniff')
  expect(headers['referrer-policy'], path).toBe('strict-origin-when-cross-origin')
}

test('public SSR preserves upstream failures instead of rendering empty 200 pages', async ({ request }) => {
  for (const path of unavailablePages) {
    const response = await request.get(path)
    expect(response.status(), path).toBe(503)
    expectSecurityHeaders(response.headers(), path)
    expect(await response.text()).toContain('服务暂时不可用')
  }
})

test('articles list stays 200 when taxonomy fails', async ({ page }) => {
  await page.context().addCookies([{
    name: 'failure-split',
    value: 'list-ok-taxonomy-down',
    domain: '127.0.0.1',
    path: '/',
  }])
  const response = await page.goto('/articles', { waitUntil: 'domcontentloaded' })
  expect(response?.status()).toBe(200)
  await expect(page.getByTestId('taxonomy-degraded')).toHaveText('栏目筛选暂不可用')
  await expect(page.getByRole('heading', { name: 'PENPOT-ARTICLES-LIST' })).toBeVisible()
  await expect(page.getByTestId('articles-empty')).toHaveCount(0)
  expect(await page.content()).not.toContain('SYSTEMS')
})

test('successful empty data stays 200 while details distinguish 404 and 500', async ({ request }) => {
  const empty = await request.get('/projects?page=2')
  expect(empty.status()).toBe(200)
  expect(await empty.text()).toContain('暂时还没有已发布项目')

  const disconnected = await request.get('/projects?page=3')
  expect(disconnected.status()).toBe(503)

  const detailCases = [
    ['/notes/2026/08/missing', 404],
    ['/projects/missing', 404],
    ['/books/2026/08/missing', 404],
    ['/notes/2026/08/broken', 500],
    ['/projects/broken', 500],
    ['/books/2026/08/broken', 500],
  ] as const
  for (const [path, status] of detailCases) {
    const response = await request.get(path)
    expect(response.status(), path).toBe(status)
    expectSecurityHeaders(response.headers(), path)
  }
})

test('admin editors do not render load failures as empty success', async ({ request }) => {
  const auth = { cookie: 'failure-session=ok' }
  const cases = [
    ['/admin/articles/1/edit', '尚未修改'],
    ['/admin/profile', '保存设置'],
  ] as const
  for (const [path, emptySuccess] of cases) {
    const response = await request.get(path, { headers: auth })
    expect(response.status(), path).toBe(503)
    expectSecurityHeaders(response.headers(), path)
    expect(await response.text(), path).not.toContain(emptySuccess)
    expect(await response.text(), path).toContain('服务暂时不可用')
  }
})

test('session 500 remains an error and 401 preserves the requested admin route', async ({ request }) => {
  const failed = await request.get('/admin/articles', { maxRedirects: 0 })
  expect(failed.status()).toBe(500)
  expectSecurityHeaders(failed.headers(), '/admin/articles')
  expect(failed.headers().location).toBeUndefined()

  const unauthorized = await request.get('/admin/projects?page=2', {
    headers: { cookie: 'failure-session=unauthorized' },
    maxRedirects: 0,
  })
  expect(unauthorized.status()).toBeGreaterThanOrEqual(300)
  expect(unauthorized.status()).toBeLessThan(400)
  expect(unauthorized.headers().location).toContain('/admin/login')
  expect(decodeURIComponent(unauthorized.headers().location || '')).toContain('/admin/projects?page=2')
})

test('login exposes its pending state before restoring an actionable error state', async ({ page }) => {
  let csrfAttempts = 0
  let loginAttempts = 0
  let markLoginStarted!: () => void
  let releaseLogin!: () => void
  const loginStarted = new Promise<void>((resolve) => {
    markLoginStarted = resolve
  })
  const loginMayFinish = new Promise<void>((resolve) => {
    releaseLogin = resolve
  })

  await page.route('**/api/v1/auth/csrf', (route) => {
    csrfAttempts += 1
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ csrf_token: 'pending-token' }),
    })
  })
  await page.route('**/api/v1/auth/login', async (route) => {
    loginAttempts += 1
    expect(route.request().headers()['x-csrf-token']).toBe('pending-token')
    markLoginStarted()
    await loginMayFinish
    await route.fulfill({
      status: 401,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'injected failure' }),
    })
  })

  await page.goto('/admin/login')
  await expectHydrated(page)
  const shell = page.getByTestId('admin-login-shell')
  const submit = page.getByTestId('login')
  await page.getByTestId('password').fill('irrelevant')
  await submit.click()
  await loginStarted

  try {
    await expect(shell).toHaveAttribute('data-state', 'submitting')
    await expect(submit).toBeDisabled()
    await expect(submit).toHaveAttribute('aria-busy', 'true')
    await expect(submit).toHaveText('验证中…')
    await expect(page.getByRole('alert')).toHaveCount(0)
    await page.getByTestId('admin-login-form').evaluate((form: HTMLFormElement) => form.requestSubmit())
    await page.waitForTimeout(100)
    expect(csrfAttempts).toBe(1)
    expect(loginAttempts).toBe(1)
  }
  finally {
    releaseLogin()
  }

  await expect(page.getByRole('alert')).toHaveText('用户名或密码不正确。')
  await expect(shell).toHaveAttribute('data-state', 'error')
  await expect(submit).toBeEnabled()
  await expect(submit).toHaveAttribute('aria-busy', 'false')
  await expect(page.getByTestId('username')).toHaveAttribute('aria-invalid', 'true')
  await expect(page.getByTestId('password')).toHaveAttribute('aria-invalid', 'true')
  await expect(page.getByTestId('password')).toHaveAttribute('aria-describedby', 'login-error')
})

test('login classifies failures and accepts only safe return targets', async ({ page }) => {
  const cases = [
    [401, '用户名或密码不正确。'],
    [403, '安全校验失败，请刷新页面后重试。'],
    [429, '尝试次数过多，请稍后再试。'],
    [500, '登录服务暂时不可用，请稍后重试。'],
  ] as const

  for (const [status, message] of cases) {
    await page.route('**/api/v1/auth/csrf', route => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ csrf_token: 'failure-token' }),
    }))
    await page.route('**/api/v1/auth/login', route => route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'injected failure' }),
    }))
    await page.goto('/admin/login')
    await expectHydrated(page)
    await expect(page.getByTestId('login')).toBeEnabled()
    await page.getByTestId('password').fill('irrelevant')
    await page.getByTestId('login').click()
    await expect(page.getByRole('alert')).toHaveText(message)
    await page.unrouteAll({ behavior: 'wait' })
  }

  await page.route('**/api/v1/auth/csrf', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ csrf_token: 'network-token' }),
  }))
  await page.route('**/api/v1/auth/login', route => route.abort('failed'))
  await page.goto('/admin/login')
  await expectHydrated(page)
  await expect(page.getByTestId('login')).toBeEnabled()
  await page.getByTestId('password').fill('irrelevant')
  await page.getByTestId('login').click()
  await expect(page.getByRole('alert')).toHaveText('无法连接登录服务，请检查网络后重试。')
  await page.unrouteAll({ behavior: 'wait' })

  await page.route('**/api/v1/auth/csrf', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ csrf_token: 'success-token' }),
  }))
  await page.route('**/api/v1/auth/login', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: '{}',
  }))
  await page.route('**/api/v1/auth/session', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ username: 'gavin' }),
  }))
  await page.route('**/api/v1/admin/projects**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: '[]',
  }))
  await page.goto('/admin/login?returnTo=%2Fadmin%2Fprojects%3Fpage%3D2')
  await expectHydrated(page)
  await expect(page.getByTestId('login')).toBeEnabled()
  await page.getByTestId('password').fill('success')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/projects\?page=2$/)
})

test('logout failure keeps the current session UI and reports uncertainty', async ({ context, page }) => {
  await context.addCookies([{
    name: 'failure-session',
    value: 'ok',
    domain: '127.0.0.1',
    path: '/',
  }])
  await page.goto('/admin/articles')
  await expect(page).toHaveURL(/\/admin\/articles$/)
  await expectHydrated(page)
  await page.locator('.admin-sidebar .admin-logout').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  await expect(page.getByTestId('logout-error')).toContainText('会话仍可能有效')
})
