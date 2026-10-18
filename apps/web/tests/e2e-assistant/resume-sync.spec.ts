import AxeBuilder from '@axe-core/playwright'
import { join } from 'node:path'
import { expect, test } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

test('resume sync shows accurate states preserves drafts and supports keyboard mobile and themes', async ({ page }, info) => {
  let view = { state: 'unconfigured', usable: false, binding_epoch: 0, request_id: null as string | null, version_id: null as string | null, last_attempt_at: null as string | null, last_checked_at: null as string | null, last_indexed_at: null as string | null, retry_at: null, error_code: null as string | null }
  let reads = 0
  let posts = 0
  let getFailure = false
  let postStatus = 202
  await page.route('**/api/v1/admin/profile/resume', route => {
    reads++
    return route.fulfill(getFailure ? { status: 503, json: { detail: 'fixture failure' } } : { json: view })
  })
  await page.route('**/api/v1/admin/profile/resume/refresh', route => {
    posts++
    expect(route.request().method()).toBe('POST')
    expect(route.request().postDataJSON()).toEqual({ binding_epoch: view.binding_epoch })
    expect(route.request().headers()['x-csrf-token']).toBeTruthy()
    if (postStatus !== 202) return route.fulfill({ status: postStatus, headers: { 'Retry-After': '1' }, json: { detail: 'fixture rejection' } })
    view = { ...view, state: 'pending', request_id: 'next-request' }
    return route.fulfill({ status: 202, json: view })
  })
  await page.goto('/admin/login')
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  await page.goto('/admin/profile')
  await expectHydrated(page)
  const card = page.getByTestId('resume-sync')
  const refresh = page.getByTestId('resume-refresh')
  await expect(card).toContainText('尚未配置简历')
  await expect(refresh).toBeDisabled()
  const url = 'https://files.example.com/resume.pdf'
  await page.getByRole('textbox', { name: '简历地址' }).fill(url)
  await expect(card).toContainText('简历地址尚未保存')
  view = { ...view, state: 'pending', binding_epoch: 1, request_id: 'initial-request' }
  await page.getByTestId('profile-save').click()
  await expect(card).toContainText('已排队，等待同步')
  expect(posts).toBe(0)
  view = { ...view, state: 'ready', usable: true, version_id: 'a'.repeat(32), last_checked_at: '2026-09-11T00:00:00Z', last_indexed_at: '2026-09-11T00:00:10Z' }
  await expect(card).toContainText('同步完成', { timeout: 10000 })
  expect(reads).toBeGreaterThan(1)
  await page.getByTestId('profile-bio').fill('Unsaved draft remains intact while refreshing.')
  await page.getByRole('textbox', { name: '简历地址' }).fill('https://files.example.com/changed.pdf')
  await expect(refresh).toBeDisabled()
  await page.getByRole('textbox', { name: '简历地址' }).fill(url)
  await expect(refresh).toBeEnabled()
  postStatus = 429
  await refresh.click()
  await expect(card).toContainText('请等待 1 秒')
  await expect(refresh).toBeDisabled()
  await expect(refresh).toBeEnabled({ timeout: 4000 })
  postStatus = 202
  await refresh.focus()
  await page.keyboard.press('Enter')
  await expect(card).toContainText('刷新请求已排队')
  await expect(page.getByTestId('profile-bio')).toHaveValue('Unsaved draft remains intact while refreshing.')
  expect(posts).toBe(2)
  view = { ...view, state: 'ready' }
  await expect(refresh).toBeEnabled({ timeout: 10000 })
  postStatus = 409
  await refresh.click()
  await expect(card).toContainText('简历地址已在别处修改')
  await expect(refresh).toBeDisabled()
  view = { ...view, state: 'failed', usable: false, error_code: 'text_unavailable' }
  await page.getByTestId('profile-save').click()
  await expect(card).toContainText('暂不支持扫描件')
  await expect(card).toContainText('助手当前不使用简历证据')
  for (const theme of ['light', 'dark']) {
    if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== (theme === 'dark')) await page.getByRole('button', { name: '切换颜色主题' }).click()
    for (const width of [1440, 390, 320]) {
      await page.setViewportSize({ width, height: 900 })
      await card.scrollIntoViewIfNeeded()
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1)
      await card.screenshot({ path: join(info.project.outputDir, 'resume', `${theme}-${width}.png`) })
    }
    const axe = await new AxeBuilder({ page }).include('[data-testid="resume-sync"]').withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
    expect(axe.violations).toEqual([])
  }
  getFailure = true
  await page.getByTestId('profile-save').click()
  await expect(card).toContainText('暂时无法读取同步状态')
  await expect(refresh).toBeDisabled()
  getFailure = false
  await card.getByRole('button', { name: '重试读取状态' }).click()
  await expect(card).toContainText('同步失败')
  view = { ...view, state: 'pending', error_code: null }
  await page.getByTestId('profile-save').click()
  await expect(card).toContainText('已排队，等待同步')
  await page.goto('/admin/articles')
  await expectHydrated(page)
  const readsAfterLeave = reads
  await page.waitForTimeout(5500)
  expect(reads).toBe(readsAfterLeave)
  expect(posts).toBe(3)
})
