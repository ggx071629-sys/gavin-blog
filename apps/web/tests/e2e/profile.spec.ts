import { join } from 'node:path'
import { expect, test, type APIRequestContext } from '@playwright/test'
import { expectHydrated as waitForHydration } from '../support/hydration'

const login = async (page: import('@playwright/test').Page) => {
  await page.goto('/admin/login', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  await expect(page.getByTestId('login')).toBeEnabled()
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
}

const profileForm = (page: import('@playwright/test').Page) =>
  page.locator('.editor-grid > div').first()

const seedUnconfiguredProfile = async (request: APIRequestContext) => {
  const csrf = await (await request.get('/api/v1/auth/csrf')).json()
  expect((await request.post('/api/v1/auth/login', { headers: { 'X-CSRF-Token': csrf.csrf_token }, data: { username: 'gavin', password: 'correct-horse' } })).ok()).toBe(true)
  const token = (await request.storageState()).cookies.find(cookie => cookie.name === 'gavin_csrf')!.value
  const current = await (await request.get('/api/v1/admin/profile')).json()
  const updated = await request.patch('/api/v1/admin/profile', {
    headers: { 'X-CSRF-Token': token },
    data: { ...current, name: 'Gavin', title: '后端工程师 / AI 应用开发者', bio: '把复杂问题写成未来仍然有用的答案。', skills: [], avatar_url: null, city: null, city_visible: false, github_url: null, website_url: null, email: null, email_visible: false, resume_url: null },
  })
  expect(updated.ok()).toBe(true)
}

test.beforeEach(async ({ request }) => {
  await seedUnconfiguredProfile(request)
})

test('homepage shows the default profile card before configuration', async ({ page }) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  const card = page.getByTestId('profile-card')
  await expect(card).toBeVisible()
  await expect(card.getByRole('heading', { name: 'Gavin' })).toBeVisible()
  await expect(card.getByTestId('profile-github')).toHaveCount(0)
  await expect(card.getByTestId('profile-website')).toHaveCount(0)
  await expect(card.getByTestId('profile-email')).toHaveCount(0)
  await expect(card.getByTestId('profile-resume')).toHaveCount(0)
})

test('admin edits the profile and visitors see the updated card', async ({ page }) => {
  await page.context().grantPermissions(['clipboard-read', 'clipboard-write'])
  await login(page)

  await page.getByRole('link', { name: '个人名片' }).click()
  await waitForHydration(page)
  await expect(page.getByRole('heading', { name: '个人名片' })).toBeVisible()
  const form = profileForm(page)
  await expect(form.getByTestId('profile-name')).toHaveValue('Gavin')

  await form.getByTestId('profile-title').fill('后端工程师 / AI 应用开发者')
  await form.getByTestId('profile-bio').fill('把复杂问题写成未来仍然有用的答案。')
  await form.getByTestId('profile-skill-input').fill('FastAPI')
  await form.getByTestId('profile-skill-add').click()
  await form.getByTestId('profile-skill-input').fill('Nuxt')
  await form.getByTestId('profile-skill-add').click()
  await form.getByTestId('profile-github').fill('https://github.com/gavinhub')
  await form.getByTestId('profile-website').fill('https://gavinhub.example.com')
  await form.getByTestId('profile-email').fill('gavin@example.com')
  await form.getByTestId('profile-email-visible').check()
  await form.getByTestId('profile-resume').fill('https://example.com/cv.pdf')

  await expect(form.getByTestId('profile-skill-item')).toHaveCount(2)
  await expect(page.getByTestId('profile-card').getByText('FastAPI')).toBeVisible()

  await page.getByTestId('profile-save').click()
  await expect(page.getByText('个人名片已更新')).toBeVisible()

  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  const card = page.getByTestId('profile-card')
  await expect(card.getByRole('heading', { name: 'Gavin' })).toBeVisible()
  await expect(card.getByText('FastAPI')).toBeVisible()
  const github = card.getByTestId('profile-github')
  await expect(github).toHaveAttribute('href', 'https://github.com/gavinhub')
  await expect(github).toHaveAttribute('target', '_blank')
  await expect(github).toHaveAttribute('rel', 'noopener noreferrer')
  await expect(github.locator('svg')).toHaveAttribute('aria-hidden', 'true')
  const website = card.getByTestId('profile-website')
  await expect(website).toHaveAttribute('href', 'https://gavinhub.example.com/')
  await expect(website).toHaveAttribute('target', '_blank')
  await expect(website).toHaveAttribute('rel', 'noopener noreferrer')
  await expect(website.locator('svg')).toHaveAttribute('aria-hidden', 'true')
  const resume = card.getByTestId('profile-resume')
  await expect(resume).toBeVisible()
  await expect(resume).toHaveAttribute('target', '_blank')
  await expect(resume).toHaveAttribute('rel', 'noopener noreferrer')
  await expect(resume.locator('svg')).toHaveAttribute('aria-hidden', 'true')

  const email = card.getByTestId('profile-email')
  await expect(email.locator('svg')).toHaveAttribute('aria-hidden', 'true')
  await email.click()
  await expect(page.getByTestId('profile-copy-feedback')).toHaveText('已复制')
})

test('hidden city and email never appear on the public card', async ({ page }) => {
  await login(page)
  await page.getByRole('link', { name: '个人名片' }).click()
  await waitForHydration(page)
  const form = profileForm(page)
  await form.getByTestId('profile-city').fill('Hangzhou')
  await form.getByTestId('profile-email').fill('gavin@example.com')
  await form.getByTestId('profile-city-visible').uncheck()
  await form.getByTestId('profile-email-visible').uncheck()
  await page.getByTestId('profile-save').click()
  await expect(page.getByText('个人名片已更新')).toBeVisible()

  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  const card = page.getByTestId('profile-card')
  await expect(card).toBeVisible()
  await expect(card.getByTestId('profile-city')).toHaveCount(0)
  await expect(card.getByTestId('profile-email')).toHaveCount(0)
})

test('warns before leaving with unsaved changes', async ({ page }) => {
  await login(page)
  await page.getByRole('link', { name: '个人名片' }).click()
  await waitForHydration(page)
  const form = profileForm(page)
  await form.getByTestId('profile-name').fill('Gavin Unsaved')
  await expect(page.getByText('有未保存修改')).toBeVisible()

  const dialogMessages: string[] = []
  page.on('dialog', async (dialog) => {
    dialogMessages.push(dialog.message())
    await dialog.dismiss()
  })
  await page.getByRole('link', { name: '文章', exact: true }).click()
  await expect(page).toHaveURL(/\/admin\/profile$/)
  expect(dialogMessages[0]).toContain('未保存')
})


test('studio profile', async ({ page }, info) => {
  test.setTimeout(180_000)
  await login(page)
  await page.goto('/admin/profile')
  await waitForHydration(page)
  const form = profileForm(page)
  for (const name of ['基本资料', '头像', '核心技能', '联系渠道']) await expect(page.getByRole('heading', { name, exact: true })).toBeVisible()
  await form.getByTestId('profile-skill-input').fill('第一技能')
  await form.getByTestId('profile-skill-add').click()
  await form.getByTestId('profile-skill-input').fill('第二技能')
  await form.getByTestId('profile-skill-add').click()
  await form.getByTestId('profile-skill-up-1').click()
  await expect(form.getByTestId('profile-skill-item').first()).toContainText('第二技能')
  await form.getByTestId('profile-skill-remove-1').click()
  await expect(form.getByTestId('profile-skill-item')).toHaveCount(1)
  await form.getByTestId('profile-city').fill('隐藏城市')
  await form.getByTestId('profile-city-visible').uncheck()
  await expect(page.getByTestId('profile-card')).not.toContainText('隐藏城市')
  await page.getByText('选择或上传头像', { exact: true }).click()
  await page.getByTestId('media-alt').fill('名片头像')
  const uploadedResponse = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/admin/media' && response.request().method() === 'POST')
  await page.getByTestId('media-file').setInputFiles({ name: 'avatar.png', mimeType: 'image/png', buffer: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=', 'base64') })
  await expect(page.getByText('已上传 1 张图片。')).toBeVisible()
  const uploadedAsset = await (await uploadedResponse).json()
  await page.getByTestId('toggle-media-library').click()
  await page.locator('.admin-media-asset').filter({ has: page.locator(`img[src$="${uploadedAsset.url}"]`) }).getByRole('button', { name: '使用 URL' }).click()
  await expect(form.getByTestId('profile-avatar-url')).toHaveValue(/media/)
  await expect(page.getByTestId('profile-avatar-preview')).toBeVisible()
  await page.getByText('选择或上传头像', { exact: true }).click()
  await form.getByTestId('profile-avatar-url').fill('https://example.com/avatar.png')
  await form.getByTestId('profile-avatar-clear').click()
  await expect(form.getByTestId('profile-avatar-url')).toBeEmpty()
  await page.getByTestId('profile-save').click()
  await expect(page.getByText('个人名片已更新')).toBeVisible()
  for (const dark of [false, true]) {
    await page.setViewportSize({ width: 1440, height: 1000 })
    if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== dark) await page.getByRole('button', { name: '切换颜色主题' }).filter({ visible: true }).click()
    for (const width of [1440, 1024, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 900 })
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1)
      await expect(page.getByTestId('profile-save')).toBeVisible()
      if ([1440, 390].includes(width)) {
        await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }))
        await page.screenshot({ path: join(info.project.outputDir, `p${dark ? 'd' : 'l'}${width}.png`), fullPage: true })
      }
    }
  }
  await page.getByRole('link', { name: '查看名片', exact: true }).click()
  await expect(page.locator('#profile-preview')).toBeInViewport()
})
