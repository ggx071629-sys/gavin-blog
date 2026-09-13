import { readFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { expect, test } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

test('versioned resume citations download exact files in public and admin answers and reject unsafe paths', async ({ page }) => {
  const fixtureResponse = await page.request.post('http://127.0.0.1:8101/api/v1/assistant/_test/resume')
  expect(fixtureResponse.ok()).toBeTruthy()
  const fixture = await fixtureResponse.json()
  const path = '/api/v1/assistant/resume/' + fixture.version_id
  const source = { n: '1', title: 'Gavin 简历', path }
  const policy = { question_max_chars: 500, session_idle_seconds: 1800, session_absolute_seconds: 14400, body_retention_seconds: 1800 }
  const turn = { turn_id: 'resume-fixture', created_at: '2026-09-11T00:00:00Z', status: 'answer', code: 'answered', message: 'ok', question: '简历有哪些自述？', answer: '简历自述从事后端工程。[1]', citations: [source], sources: [source], body_available: true }
  await page.route('**/api/v1/assistant/**', route => {
    const url = new URL(route.request().url())
    if (url.pathname.startsWith('/api/v1/assistant/resume/')) return route.continue()
    if (url.pathname.endsWith('/availability')) return route.fulfill({ json: { available: true } })
    if (url.pathname.endsWith('/sessions')) return route.fulfill({ json: { policy } })
    return route.fulfill({ json: { session_id: 'resume-isolated', created_at: '2026-09-11', idle_expires_at: '2026-09-12', absolute_expires_at: '2026-09-12', policy, turns: [turn], active_turn: null } })
  })
  await page.goto('/')
  await expectHydrated(page)
  await page.getByTestId('assistant-launcher').click()
  await page.getByRole('button', { name: '范围与数据说明' }).click()
  await expect(page.getByText('这是 AI，不是站长本人。', { exact: false })).toContainText('站长导入的公开简历')
  const publicLink = page.locator('.assistant-source-link').filter({ hasText: 'Gavin 简历' })
  await expect(publicLink).toHaveAttribute('href', path)
  await expect(publicLink).toHaveAttribute('download', '')
  await publicLink.focus()
  const firstDownload = page.waitForEvent('download')
  await page.keyboard.press('Enter')
  const first = await firstDownload
  expect(first.suggestedFilename()).toBe('gavin-resume.pdf')
  expect(createHash('sha256').update(await readFile((await first.path())!)).digest('hex')).toBe(fixture.sha256)
  const response = await page.request.get(path)
  expect(response.status()).toBe(200)
  expect(response.headers()['cache-control']).toBe('no-store')
  expect(response.headers()['x-content-type-options']).toBe('nosniff')
  expect(response.headers()['content-disposition']).toContain('attachment')
  expect((await page.request.get('/api/v1/assistant/resume/' + '0'.repeat(32))).status()).toBe(404)
  expect((await page.request.get(path + '?url=https://evil.invalid')).status()).toBe(404)
  await expect(page).toHaveURL(/\/$/)
  for (const unsafe of [path + '?url=https://evil.invalid', path.toUpperCase(), '/api/v1/assistant/resume/%61' + 'a'.repeat(31), 'https://evil.invalid/resume.pdf']) {
    source.path = unsafe
    await page.goto('/')
    await expectHydrated(page)
    await page.getByTestId('assistant-launcher').click()
    await expect(page.locator('.assistant-source-link')).toHaveCount(0)
  }
  source.path = '/about'
  await page.goto('/')
  await expectHydrated(page)
  await page.getByTestId('assistant-launcher').click()
  const webLink = page.locator('.assistant-source-link')
  await expect(webLink).not.toHaveAttribute('download')
  await webLink.click()
  await expect(page).toHaveURL(/\/about$/)
  source.path = path
  await page.goto('/admin/login')
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  await page.route('**/api/v1/admin/assistant/trial/session', route => route.fulfill({ json: {
    turns: [{ ...turn, cost_micro_cny: 0, citations: [{ ...source, excerpt: '简历自述从事后端工程。' }] }], active_turn: null,
  } }))
  await page.goto('/admin/assistant?view=test')
  await expectHydrated(page)
  await page.getByText('查看回答依据（1 处）').click()
  const adminLink = page.locator('.am-source a')
  await expect(adminLink).toHaveAttribute('href', path)
  await expect(adminLink).toContainText('下载简历 PDF')
  const secondDownload = page.waitForEvent('download')
  await adminLink.click()
  const second = await secondDownload
  expect(createHash('sha256').update(await readFile((await second.path())!)).digest('hex')).toBe(fixture.sha256)
})
