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

const publishProject = async (page: Page, csrf: string, title: string, slug: string) => {
  const created = await page.request.post('/api/v1/admin/projects', {
    headers: { 'X-CSRF-Token': csrf },
    data: {
      title,
      slug,
      summary: `${title} summary`,
      content: `# ${title}\n\nbody`,
      repository_url: null,
      website_url: null,
      article_ids: [],
    },
  })
  expect(created.status(), title).toBe(201)
  const project = await created.json()
  const published = await page.request.post(`/api/v1/admin/projects/${project.id}/publish`, {
    headers: { 'X-CSRF-Token': csrf },
    data: { version: project.version },
  })
  expect(published.ok(), title).toBeTruthy()
  return published.json()
}

const trashAllProjects = async (page: Page, csrf: string) => {
  const listed = await page.request.get('/api/v1/admin/projects?limit=100&offset=0')
  expect(listed.ok()).toBeTruthy()
  const projects = await listed.json() as { id: number }[]
  for (const project of projects) {
    const trashed = await page.request.delete(`/api/v1/admin/projects/${project.id}`, {
      headers: { 'X-CSRF-Token': csrf },
    })
    expect(trashed.status(), String(project.id)).toBe(204)
  }
}

test('empty projects index stays 200 without a lead', async ({ page }) => {
  const csrf = await loginAndCsrf(page)
  await trashAllProjects(page, csrf)
  await page.goto('/projects', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await expect(page.getByText('暂时还没有已发布项目。')).toBeVisible()
  await expect(page.getByTestId('projects-lead')).toHaveCount(0)
})

test('one published project is lead only', async ({ page }) => {
  test.setTimeout(120_000)
  const csrf = await loginAndCsrf(page)
  await trashAllProjects(page, csrf)
  await publishProject(page, csrf, 'PENPOT-PROJECTS-ONLY', 'penpot-projects-only')
  await page.goto('/projects', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await expect(page.getByTestId('projects-lead')).toContainText('PENPOT-PROJECTS-ONLY')
  await expect(page.getByTestId('project-card')).toHaveCount(0)
  await expect(page.getByText('暂时还没有已发布项目。')).toHaveCount(0)
})

test('projects lead is the current page first item and ledger skips it', async ({ page }) => {
  test.setTimeout(180_000)
  const csrf = await loginAndCsrf(page)
  for (let index = 0; index < 13; index += 1) {
    await publishProject(page, csrf, `PENPOT-PROJECTS-ROW-${index + 1}`, `penpot-projects-row-${index + 1}`)
  }
  await publishProject(page, csrf, 'PENPOT-PROJECTS-LEAD', 'penpot-projects-lead')

  await page.goto('/projects', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  const body = await page.locator('body').innerText()
  expect(body).not.toContain('ACTIVE')
  expect(body).not.toContain('435 / 435')
  expect(body).not.toContain('RELEASE CANDIDATE')
  expect(body.toLowerCase()).not.toContain('featured')
  expect(body).not.toContain('主项目')
  await expect(page.getByTestId('projects-lead')).toContainText('PENPOT-PROJECTS-LEAD')
  await expect(page.getByTestId('project-card').filter({ hasText: 'PENPOT-PROJECTS-LEAD' })).toHaveCount(0)
  await expect(page.locator('.projects-index-layout')).toHaveCount(0)

  const pageTwo = await page.request.get('/api/v1/projects?limit=12&offset=12')
  expect(pageTwo.ok()).toBeTruthy()
  const pageTwoItems = await pageTwo.json() as { title: string }[]
  expect(pageTwoItems.length).toBeGreaterThan(0)

  await page.getByTestId('pagination-next').click()
  await expect(page).toHaveURL(/page=2/)
  await expectHydrated(page)
  await expect(page.getByTestId('projects-lead')).toContainText(pageTwoItems[0]!.title)
  await expect(page.getByTestId('projects-lead')).not.toContainText('PENPOT-PROJECTS-LEAD')

  await page.setViewportSize({ width: 1024, height: 800 })
  await expect(page.getByRole('button', { name: '打开主导航菜单' })).toBeVisible()
})
