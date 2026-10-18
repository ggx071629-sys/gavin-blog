import { expect, test, type Page } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

const loginAndCsrf = async (page: Page) => {
  await page.goto('/admin/login', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  const csrf = (await page.context().cookies()).find(cookie => cookie.name === 'gavin_csrf')?.value
  expect(csrf).toBeTruthy()
  return csrf!
}

const patchProfile = async (page: Page, csrf: string, extras: Record<string, unknown>) => {
  const current = await page.request.get('/api/v1/admin/profile')
  expect(current.ok()).toBeTruthy()
  const profile = await current.json()
  const updated = await page.request.patch('/api/v1/admin/profile', {
    headers: { 'X-CSRF-Token': csrf },
    data: {
      name: profile.name,
      title: profile.title,
      bio: profile.bio,
      skills: profile.skills,
      avatar_url: profile.avatar_url,
      city: profile.city,
      city_visible: profile.city_visible,
      github_url: profile.github_url,
      website_url: profile.website_url,
      email: profile.email,
      email_visible: profile.email_visible,
      resume_url: profile.resume_url,
      version: profile.version,
      ...extras,
    },
  })
  expect(updated.ok()).toBeTruthy()
  return updated.json()
}

test('about keeps static brand copy and real profile fields', async ({ page }) => {
  test.setTimeout(120_000)
  const csrf = await loginAndCsrf(page)
  const publishedAbout = await (await page.request.get('/api/v1/about-page')).json()
  expect(publishedAbout.capabilities.length).toBeGreaterThan(0)
  await patchProfile(page, csrf, {
    city: 'PENPOT-ABOUT-CITY',
    city_visible: true,
    email: 'penpot-about@example.com',
    email_visible: true,
    github_url: 'https://github.com/penpot-about',
    skills: ['PENPOT-ABOUT-SKILL'],
  })

  await page.goto('/about', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  const body = await page.locator('body').innerText()
  expect(body).not.toContain('SHANGHAI')
  expect(body).not.toContain('UTC+8')
  expect(body).not.toContain('LAST REVISED')
  expect(body).not.toContain('INTER + JETBRAINS MONO')
  await expect(page.getByText('SYS.ID / GVN-01')).toHaveCount(0)
  await expect(page.getByRole('heading', { level: 1 })).toContainText('我是')
  await expect(page.getByRole('heading', { name: '我能做什么' })).toBeVisible()
  await expect(page.locator('.about-capability')).toHaveCount(publishedAbout.capabilities.length)
  for (const capability of publishedAbout.capabilities) {
    await expect(page.locator('.about-capability').filter({ hasText: capability.title })).toContainText(capability.description)
  }
  await expect(page.getByRole('link', { name: 'RSS 订阅' })).toBeVisible()
  await expect(page.getByTestId('about-coordinates')).toContainText('PENPOT-ABOUT-CITY')
  await expect(page.getByTestId('about-coordinates')).toContainText('PENPOT-ABOUT-SKILL')
  await expect(page.getByRole('link', { name: '写作台', exact: true })).toBeVisible()
  expect(await page.locator('h1').evaluate(el => getComputedStyle(el).fontFamily)).toContain('Space Grotesk')

  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await expect(page.getByTestId('profile-card')).toBeVisible()
  await expect(page.getByTestId('profile-card')).toContainText('PENPOT-ABOUT-CITY')
  await expect(page.getByTestId('profile-card')).toContainText('PENPOT-ABOUT-SKILL')
})

test('about omits missing profile fields instead of filling dummy Now', async ({ page }) => {
  test.setTimeout(120_000)
  const csrf = await loginAndCsrf(page)
  await patchProfile(page, csrf, {
    city: null,
    city_visible: false,
    email: null,
    email_visible: false,
    github_url: null,
    resume_url: null,
    avatar_url: null,
    skills: [],
  })

  await page.goto('/about', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  const body = await page.locator('body').innerText()
  expect(body).not.toContain('SHANGHAI')
  expect(body).not.toContain('UTC+8')
  await expect(page.getByText('SYS.ID / GVN-01')).toHaveCount(0)
  await expect(page.getByRole('heading', { level: 1 })).toContainText('我是')
  await expect(page.getByRole('link', { name: 'RSS 订阅' })).toBeVisible()
  await expect(page.getByTestId('about-coordinates').getByText('Email')).toHaveCount(0)
  await expect(page.getByTestId('about-coordinates').getByText('GitHub')).toHaveCount(0)

  await page.setViewportSize({ width: 1024, height: 800 })
  await expect(page.getByRole('button', { name: '打开主导航菜单' })).toBeVisible()
})
