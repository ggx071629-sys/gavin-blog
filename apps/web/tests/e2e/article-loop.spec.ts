import { expect, test } from '@playwright/test'
import { expectHydrated as waitForHydration } from '../support/hydration'

test('loop', async ({ page }) => {
  await page.goto('/admin/login', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  // Wait until Nuxt has hydrated the form before entering credentials.
  await expect(page.getByTestId('login')).toBeEnabled()
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)

  await page.getByRole('link', { name: '栏目与标签' }).click()
  await page.getByTestId('categories-name').fill('工程实践')
  await page.getByTestId('categories-slug').fill('engineering')
  await page.getByTestId('categories-submit').click()
  await expect(page.getByTestId('taxonomy-categories').getByText('工程实践')).toBeVisible()
  await page.getByTestId('tags-name').fill('FastAPI')
  await page.getByTestId('tags-slug').fill('fastapi')
  await page.getByTestId('tags-submit').click()
  await expect(page.getByTestId('taxonomy-tags').getByRole('heading', { name: 'FastAPI', exact: true })).toBeVisible()

  await page.getByRole('link', { name: '文章', exact: true }).click()
  await page.locator('.studio-content-list > header').getByRole('link', { name: '新建草稿' }).click()
  let articleCreateRequests = 0
  page.on('request', (request) => {
    if (request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/admin/articles') {
      articleCreateRequests += 1
    }
  })
  await page.getByTestId('new-title').fill('纯中文标题')
  await expect(page.getByTestId('new-slug')).toHaveValue('')
  await page.getByTestId('create-draft').click()
  await expect(page.getByText('当前标题无法自动生成 Slug，请填写英文或拼音 Slug。')).toBeVisible()
  await expect(page.getByTestId('new-slug')).toHaveAttribute('aria-invalid', 'true')
  expect(articleCreateRequests).toBe(0)

  await page.getByTestId('new-title').fill('Harness Engineering')
  await page.getByTestId('new-slug').fill('harness-engineering')
  await page.getByTestId('new-content').fill('# First draft')
  await page.getByTestId('new-category').selectOption({ label: '工程实践' })
  await page.getByTestId('new-tag-fastapi').check()
  await page.getByTestId('create-draft').click()
  await expect(page).toHaveURL(/\/admin\/articles\/\d+\/edit$/)
  expect(articleCreateRequests).toBe(1)
  const articleId = page.url().match(/\/admin\/articles\/(\d+)\/edit$/)?.[1]
  expect(articleId).toBeTruthy()

  await page.getByTestId('content').fill('# Published\n\nA verified article loop.')
  await page.getByRole('link', { name: '预览' }).click()
  await expect(page.getByText('草稿预览，不会出现在公开站点。')).toBeVisible()
  await expect(page.getByText('A verified article loop.')).toBeVisible()
  await page.getByRole('link', { name: '返回编辑' }).click()
  await page.getByTestId('content').fill('# Saved before sidebar navigation')
  await page.getByRole('link', { name: '文章', exact: true }).click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  const savedBeforeNavigation = await page.request.get(`/api/v1/admin/articles/${articleId}`)
  expect(savedBeforeNavigation.ok()).toBeTruthy()
  expect((await savedBeforeNavigation.json()).content).toBe('# Saved before sidebar navigation')
  await page.goto(`/admin/articles/${articleId}/edit`)
  await waitForHydration(page)
  await page.getByTestId('content').fill('# Published\n\nA verified article loop.')
  await page.getByTestId('publish').click()
  await page.getByTestId('confirm-publish').click()
  await expect(page).toHaveURL(/\/notes\/\d{4}\/\d{2}\/harness-engineering$/)
  await expect(page.getByRole('heading', { name: 'Harness Engineering' })).toBeVisible()
  await expect(page.getByText('A verified article loop.')).toBeVisible()
  await expect(page.getByRole('link', { name: '工程实践' })).toBeVisible()
  await page.getByRole('link', { name: 'FastAPI', exact: true }).click()
  await expect(page).toHaveURL(/\/articles\?tag=fastapi$/)
  await expect(page.getByRole('heading', { name: 'Harness Engineering' })).toBeVisible()

  await page.goto('/admin/projects')
  await waitForHydration(page)
  await page.locator('.studio-content-list > header').getByRole('link', { name: '新建项目' }).click()
  await page.getByTestId('new-project-title').fill('Gavin Blog')
  await page.getByTestId('new-project-slug').fill('gavin-blog')
  await page.getByTestId('new-project-content').fill('# Project draft')
  await page.getByTestId('project-article-harness-engineering').check()
  await page.getByTestId('create-project').click()
  await expect(page).toHaveURL(/\/admin\/projects\/\d+\/edit$/)
  await page.getByTestId('project-content').fill('# Gavin Blog\n\nA public project case study.')
  await expect(page.getByText('已自动保存')).toBeVisible()
  await page.getByTestId('publish-project').click()
  await page.getByTestId('confirm-publish').click()
  await expect(page).toHaveURL(/\/projects\/gavin-blog$/)
  await expect(page.locator('article > header h1')).toHaveText('Gavin Blog')
  await expect(page.getByRole('link', { name: 'Harness Engineering' })).toBeVisible()

  await page.goto('/admin/books')
  await waitForHydration(page)
  await page.locator('.studio-content-list > header').getByRole('link', { name: '新建读书笔记' }).click()
  await page.getByTestId('new-book-title').fill('Designing Data-Intensive Applications')
  await page.getByTestId('new-book-author').fill('Martin Kleppmann')
  await page.getByTestId('new-book-slug').fill('designing-data-intensive-applications')
  await page.getByTestId('new-book-content').fill('# Book draft')
  await page.getByTestId('create-book').click()
  await expect(page).toHaveURL(/\/admin\/books\/\d+\/edit$/)
  await page.getByTestId('book-reading-status').selectOption('completed')
  await page.getByTestId('book-content').fill('# Finished\n\nDurability needs explicit trade-offs.')
  await expect(page.getByText('已自动保存')).toBeVisible()
  await page.getByTestId('publish-book').click()
  await page.getByTestId('confirm-publish').click()
  await expect(page).toHaveURL(/\/books\/\d{4}\/\d{2}\/designing-data-intensive-applications$/)
  await expect(page.getByRole('heading', { name: 'Designing Data-Intensive Applications' })).toBeVisible()
  await expect(page.getByText('Martin Kleppmann')).toBeVisible()

  await page.goto('/search')
  await waitForHydration(page)
  await page.getByTestId('search-input').fill('Harness')
  await page.getByTestId('search-submit').click()
  await expect(page).toHaveURL(/\/search\?q=Harness$/)
  await expect(page.getByRole('heading', { name: 'Harness Engineering' })).toBeVisible()

  await page.goto('/admin/media')
  await waitForHydration(page)
  await page.getByTestId('media-alt').fill('A blue test pixel')
  await page.getByTestId('media-file').setInputFiles({
    name: 'pixel.png',
    mimeType: 'image/png',
    buffer: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=', 'base64'),
  })
  await expect(page.getByText('已上传 1 张图片。')).toBeVisible()
  await expect(page.getByText('WEBP · AVIF')).toBeVisible()

  await page.goto('/admin/projects')
  await waitForHydration(page)
  page.once('dialog', dialog => dialog.accept())
  await page.getByRole('button', { name: 'Gavin Blog的更多操作', exact: true }).click()
  await page.getByRole('dialog').getByRole('button', { name: '移入回收站', exact: true }).click()
  await expect(page.getByRole('article').filter({ hasText: 'Gavin Blog' })).toHaveCount(0)
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await page.goto('/admin/content')
  await waitForHydration(page)
  const trashedProject = page.getByRole('article').filter({ hasText: 'Gavin Blog' })
  await expect(trashedProject).toBeVisible()
  await trashedProject.getByRole('button', { name: '恢复' }).click()
  await expect(trashedProject).toHaveCount(0)
  const restoredProject = await page.request.get('/api/v1/projects/gavin-blog')
  expect(restoredProject.status()).toBe(200)
  expect((await restoredProject.json()).title).toBe('Gavin Blog')

  const downloadPromise = page.waitForEvent('download')
  await page.getByTestId('export-markdown').click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toContain('gavin-markdown')

  const importedDocument = [
    '---',
    JSON.stringify({ type: 'article', title: 'Imported E2E', slug: 'imported-e2e', summary: 'Portable' }),
    '---',
    '',
    '# Imported from Markdown',
  ].join('\n')
  await page.getByTestId('import-markdown').setInputFiles({
    name: 'imported-e2e.md',
    mimeType: 'text/markdown',
    buffer: Buffer.from(importedDocument),
  })
  await expect(page.getByText('已导入 1 项草稿。')).toBeVisible()
  await page.getByRole('link', { name: '文章', exact: true }).click()
  await expect(page.getByText('Imported E2E')).toBeVisible()

  const csrf = (await page.context().cookies()).find(cookie => cookie.name === 'gavin_csrf')?.value
  expect(csrf).toBeTruthy()
  for (let index = 0; index < 20; index += 1) {
    const response = await page.request.post('/api/v1/admin/articles', {
      headers: { 'X-CSRF-Token': csrf! },
      data: {
        title: `Pagination draft ${index}`,
        slug: `pagination-draft-${index}`,
      },
    })
    expect(response.ok()).toBeTruthy()
  }
  await page.goto('/admin/articles')
  await waitForHydration(page)
  await page.getByTestId('pagination-next').click()
  await expect(page).toHaveURL(/\/admin\/articles\?page=2$/)
  await expect(page.getByTestId('pagination-previous')).toBeVisible()
})
