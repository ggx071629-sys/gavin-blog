import { expect, test } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

test('each citation retains its own safe location and keyboard return after restore', async ({ page }) => {
  const source = { n: '1', title: '关于 Gavin', path: '/about' }
  const citations = [
    { ...source, heading_path: '自述 <em>文本</em>' },
    { ...source, n: '2', heading_path: '写作主题' },
    { n: '3', title: '简历', path: '/api/v1/assistant/resume/' + 'a'.repeat(32), heading_path: '第 2 页' },
    { ...source, n: '4' },
  ]
  const policy = { question_max_chars: 500, session_idle_seconds: 1800, session_absolute_seconds: 14400, body_retention_seconds: 1800 }
  const turn = { turn_id: 'locations', created_at: '2026-09-12', status: 'answer', code: 'answered', message: 'ok', question: '核查来源', answer: '自述。[1]主题。[2]简历。[3]正文。[4]', citations, sources: [source, citations[2]], body_available: true }
  await page.route('**/api/v1/assistant/**', route => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/availability')) return route.fulfill({ json: { available: true } })
    if (path.endsWith('/sessions')) return route.fulfill({ json: { policy } })
    return route.fulfill({ json: { session_id: 'locations', created_at: '2026-09-12', idle_expires_at: '2026-09-12', absolute_expires_at: '2026-09-12', policy, turns: [turn], active_turn: null } })
  })
  for (let restore = 0; restore < 2; restore++) {
    await page.goto('/')
    await expectHydrated(page)
    await page.getByTestId('assistant-launcher').click()
    for (const [n, location] of [['1', '自述 <em>文本</em>'], ['2', '写作主题'], ['3', '第 2 页'], ['4', '未提供章节定位']]) {
      const marker = page.getByRole('button', { name: `查看来源 ${n}`, exact: true })
      await marker.focus()
      await page.keyboard.press('Enter')
      const row = page.locator(`#assistant-source-locations-${n}`)
      await expect(row).toBeFocused()
      await expect(row).toContainText(location!)
      await expect(row.locator('em')).toHaveCount(0)
      await row.getByRole('button', { name: '返回引用' }).click()
      await expect(marker).toBeFocused()
    }
  }
  citations[1]!.path = 'https://untrusted.invalid/'
  await page.reload()
  await expectHydrated(page)
  await page.getByTestId('assistant-launcher').click()
  await expect(page.locator('.assistant-source-link')).toHaveCount(0)
})

test('about citations navigate in public answers and admin trial', async ({ page }) => {
  const source = { n: '1', title: '关于 Gavin', path: '/about' }
  const policy = { question_max_chars: 500, session_idle_seconds: 1800, session_absolute_seconds: 14400, body_retention_seconds: 1800 }
  const turn = { turn_id: 'about-fixture', created_at: '2026-09-11T00:00:00Z', status: 'answer', code: 'answered', message: 'ok', question: '关于页有哪些自述？', answer: '关于页列出了工程方向。[1]', citations: [source], sources: [source], body_available: true }
  await page.route('**/api/v1/assistant/**', route => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/availability')) return route.fulfill({ json: { available: true } })
    if (path.endsWith('/sessions')) return route.fulfill({ json: { policy } })
    return route.fulfill({ json: { session_id: 'about-isolated', created_at: '2026-09-11', idle_expires_at: '2026-09-12', absolute_expires_at: '2026-09-12', policy, turns: [turn], active_turn: null } })
  })
  await page.goto('/')
  await expectHydrated(page)
  await page.getByTestId('assistant-launcher').click()
  const publicLink = page.locator('.assistant-source-link').filter({ hasText: '关于 Gavin' })
  await expect(publicLink).toHaveAttribute('href', '/about')
  await publicLink.click()
  await expect(page).toHaveURL(/\/about$/)
  await expectHydrated(page)
  source.path = 'https://untrusted.invalid/about'
  await page.goto('/')
  await expectHydrated(page)
  await page.getByTestId('assistant-launcher').click()
  await expect(page.locator('.assistant-source-link')).toHaveCount(0)
  source.path = '/about'
  await page.goto('/admin/login')
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  await page.route('**/api/v1/admin/assistant/trial/session', route => route.fulfill({ json: {
    turns: [{ ...turn, cost_micro_cny: 0, citations: [{ ...source, excerpt: '关于页列出了工程方向。' }] }], active_turn: null,
  } }))
  await page.goto('/admin/assistant?view=test')
  await expectHydrated(page)
  await page.getByText('查看回答依据（1 处）').click()
  const adminLink = page.locator('.am-source a')
  await expect(adminLink).toHaveAttribute('href', '/about')
  const popupPromise = page.waitForEvent('popup')
  await adminLink.click()
  const popup = await popupPromise
  await expect(popup).toHaveURL(/\/about$/)
  await popup.close()
})
