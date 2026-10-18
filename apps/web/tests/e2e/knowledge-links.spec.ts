import { expect, test } from '@playwright/test'
import { expectHydrated as waitForHydration } from '../support/hydration'

test('published wikilinks and article references create public backlinks', async ({ page }) => {
  await page.goto('/admin/login', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  await expect(page.getByTestId('login')).toBeEnabled()
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)

  const csrf = (await page.context().cookies()).find(cookie => cookie.name === 'gavin_csrf')?.value
  expect(csrf).toBeTruthy()
  const headers = { 'X-CSRF-Token': csrf! }

  const createAndPublish = async (title: string, slug: string, content: string, extra: Record<string, unknown> = {}) => {
    const createdResponse = await page.request.post('/api/v1/admin/articles', {
      headers,
      data: { title, slug, content, ...extra },
    })
    expect(createdResponse.status()).toBe(201)
    const created = await createdResponse.json()
    const publishedResponse = await page.request.post(`/api/v1/admin/articles/${created.id}/publish`, {
      headers,
      data: { version: created.version },
    })
    expect(publishedResponse.ok()).toBeTruthy()
    return publishedResponse.json()
  }

  const target = await createAndPublish('知识网络目标', 'knowledge-target', '# 目标\n\n被引用的笔记。')
  const source = await createAndPublish(
    '知识网络来源',
    'knowledge-source',
    '# 来源\n\n继续看 [[knowledge-target|目标笔记]]。',
    {
      references: [
        {
          kind: 'internal',
          display_title: '目标笔记',
          target_type: 'article',
          target_id: target.id,
        },
      ],
    },
  )

  await page.goto(source.public_path)
  await waitForHydration(page)
  await expect(page.getByRole('link', { name: '目标笔记' }).first()).toBeVisible()
  await page.getByRole('link', { name: '目标笔记' }).first().click()
  await expect(page).toHaveURL(new RegExp(`${target.public_path}$`))
  await expect(page.getByTestId('content-backlinks')).toBeVisible()
  await expect(page.getByTestId('content-backlinks').getByRole('link', { name: '知识网络来源' })).toBeVisible()

  const draftPatch = await page.request.patch(`/api/v1/admin/articles/${source.id}`, {
    headers,
    data: { content: '# 来源\n\n未发布的 [[knowledge-target]] 修改。', version: source.version },
  })
  expect(draftPatch.ok()).toBeTruthy()
  await page.goto(target.public_path)
  await waitForHydration(page)
  await expect(page.getByTestId('content-backlinks').getByRole('link', { name: '知识网络来源' })).toBeVisible()

  await page.goto(`/admin/articles/${source.id}/edit`)
  await waitForHydration(page)
  await expect(page.getByTestId('article-references')).toBeVisible()
  await expect(page.getByTestId('reference-title-0')).toHaveValue('目标笔记')
})
