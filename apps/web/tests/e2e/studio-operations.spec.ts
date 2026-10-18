import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

const open = async (page: Page, path: string) => { await page.goto(path); await expectHydrated(page) }
const login = async (page: Page) => {
  await open(page, '/admin/login')
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
}

test('o1', async ({ page }, info) => {
  test.setTimeout(300_000)
  await login(page)
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  const failures: unknown[] = []
  for (const path of ['/admin/profile', '/admin/about', '/admin/about/preview', '/admin/about/revisions', '/admin/taxonomy', '/admin/media', '/admin/content']) {
    await open(page, path)
    await expect(page.locator('#admin-main h1')).toHaveCount(1)
    for (const dark of [false, true]) {
      await page.setViewportSize({ width: 1440, height: 1000 })
      if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== dark) await page.getByRole('button', { name: '切换颜色主题' }).filter({ visible: true }).click()
      for (const width of [1440, 1024, 768, 390, 320]) {
        await page.setViewportSize({ width, height: 900 })
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
        if (overflow > 1) failures.push({ path, dark, width, overflow })
        await expect(page.locator('#admin-main h1')).toBeVisible()
      }
      await expect.poll(() => page.evaluate(() => document.getAnimations().filter(animation => animation instanceof CSSTransition && animation.playState === 'running' && animation.effect instanceof KeyframeEffect && animation.effect.target instanceof Element && animation.effect.target.closest('#admin-main')).length)).toBe(0)
      const result = await new AxeBuilder({ page }).include('#admin-main').withTags(['wcag2a', 'wcag2aa']).analyze()
      for (const violation of result.violations) failures.push({ path, dark, id: violation.id, nodes: violation.nodes.map(node => ({ target: node.target, summary: node.failureSummary })) })
    }
  }
  await info.attach('operations-checks', { body: JSON.stringify({ viewports: 70, accessibilityScans: 14, failures, errors }), contentType: 'application/json' })
  expect(errors).toEqual([])
  expect(failures).toEqual([])
})

test('o2', async ({ page }) => {
  test.setTimeout(150_000)
  await login(page)
  await open(page, '/admin/profile')
  await page.getByTestId('profile-name').fill('冲突保留输入')
  await page.route('**/api/v1/admin/profile', route => route.request().method() === 'PATCH' ? route.fulfill({ status: 409, json: { detail: 'conflict' } }) : route.continue())
  await page.getByTestId('profile-save').click()
  await expect(page.getByTestId('profile-conflict')).toBeVisible()
  await expect(page.getByTestId('profile-name')).toHaveValue('冲突保留输入')
  await page.unroute('**/api/v1/admin/profile')
  await page.getByTestId('profile-refresh').click()
  await expect(page.getByTestId('profile-conflict')).toHaveCount(0)
  await open(page, '/admin/about')
  await page.route('**/api/v1/admin/about-page', route => route.request().method() === 'PATCH' ? route.fulfill({ status: 503, json: { detail: '保存失败' } }) : route.continue())
  await page.getByTestId('about-statement').fill('失败重试草稿')
  await page.getByTestId('about-preview-open').click()
  await expect(page).toHaveURL(/\/admin\/about$/)
  await expect(page.getByTestId('about-statement')).toHaveValue('失败重试草稿')
  await expect(page.locator('.save-state')).toContainText('保存失败')
  await page.unroute('**/api/v1/admin/about-page')
  await page.getByTestId('about-preview-open').click()
  await expect(page).toHaveURL(/\/admin\/about\/preview$/)
  await expect(page.getByTestId('about-preview-statement')).toHaveText('失败重试草稿')
  await page.route('**/api/v1/admin/about-page/revisions', route => route.fulfill({ status: 503, json: { detail: '历史读取失败' } }))
  await page.getByRole('link', { name: '版本历史', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('历史读取失败')
  await expect(page.getByText('暂无发布修订。')).toHaveCount(0)
  await page.unroute('**/api/v1/admin/about-page/revisions')
  await page.getByRole('button', { name: '重新读取历史' }).click()
  await expect(page.getByTestId('about-revision-view')).not.toHaveCount(0)
  await expect(page.getByRole('alert')).toHaveCount(0)
  // Empty states have explicit fixtures; prior cases may populate the shared API.
  await page.route('**/api/v1/admin/media?**', route => route.fulfill({ json: [] }))
  await page.route('**/api/v1/admin/trash*', route => route.fulfill({ json: [] }))
  await page.route('**/api/v1/admin/tags', route => route.fulfill({ json: [] }))
  await page.locator('.admin-sidebar a[href="/admin/media"]').click()
  await expect(page.getByText('当前筛选下没有媒体。')).toBeVisible()
  await page.locator('.admin-sidebar a[href="/admin/content"]').click()
  await expect(page.getByText('回收站为空。')).toBeVisible()
  await page.locator('.admin-sidebar a[href="/admin/taxonomy"]').click()
  await expect(page.getByTestId('taxonomy-tags').getByText('尚未创建。')).toBeVisible()
})
