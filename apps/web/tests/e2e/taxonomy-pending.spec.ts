import { expect, test, type Page, type Route } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

async function openTaxonomy(page: Page) {
  await page.goto('/admin/login')
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  await page.goto('/admin/taxonomy')
  await expectHydrated(page)
  return { 'X-CSRF-Token': (await page.context().cookies()).find(c => c.name === 'gavin_csrf')!.value }
}

async function hold(page: Page, endpoint: string, method: string, forward = false) {
  let release!: () => void
  let received!: (status: number | undefined) => void
  let requests = 0
  const waiting = new Promise<void>(resolve => { release = resolve })
  const started = new Promise<number | undefined>(resolve => { received = resolve })
  const handler = async (route: Route) => {
    if (route.request().method() !== method) return route.continue()
    requests += 1
    // When forwarding, the real API commits before only the response is withheld.
    const response = forward ? await route.fetch() : undefined
    received(response?.status())
    await waiting
    try {
      if (response) await route.fulfill({ response })
      else await route.abort('timedout')
    }
    catch { /* The browser may already have aborted this held request. */ }
  }
  await page.route(endpoint, handler)
  return {
    started,
    count: () => requests,
    async cleanup() { release(); await page.unroute(endpoint, handler) },
  }
}

test('taxonomy stalled creates release pending and preserve both forms without replay', async ({ page }) => {
  test.setTimeout(100_000)
  await openTaxonomy(page)
  for (const kind of ['tags', 'categories']) {
    const name = `pending-${kind}-${Date.now()}`
    const section = page.getByTestId(`taxonomy-${kind}`)
    await page.getByTestId(`${kind}-name`).fill(name)
    await page.getByTestId(`${kind}-slug`).fill(name)
    await section.getByLabel('说明', { exact: true }).fill('保留说明')
    const stalled = await hold(page, `**/api/v1/admin/${kind}`, 'POST')
    try {
      const submit = page.getByTestId(`${kind}-submit`)
      await submit.click()
      await stalled.started
      await expect(submit).toBeDisabled()
      await expect(submit).toBeEnabled({ timeout: 18_000 })
      await expect(section.getByRole('alert')).toContainText('保存结果尚未确认')
      await expect(page.getByTestId(`${kind}-name`)).toHaveValue(name)
      await expect(page.getByTestId(`${kind}-slug`)).toHaveValue(name)
      await expect(section.getByLabel('说明', { exact: true })).toHaveValue('保留说明')
      await expect(section.getByRole('button', { name: '核对最新列表' })).toBeVisible()
      expect(stalled.count()).toBe(1)
      const actual = await page.request.get(`/api/v1/admin/${kind}`)
      expect(actual.status()).toBe(200)
      expect((await actual.json()).some((item: { slug: string }) => item.slug === name)).toBe(false)
    }
    finally { await stalled.cleanup() }
  }
})

test('taxonomy lost save response reconciles real data and bounds a stalled read', async ({ page }) => {
  test.setTimeout(110_000)
  await openTaxonomy(page)
  const section = page.getByTestId('taxonomy-tags')
  const name = `committed-${Date.now()}`
  let writes = 0
  page.on('request', request => { if (request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/admin/tags') writes += 1 })
  await page.getByTestId('tags-name').fill(name)
  await page.getByTestId('tags-slug').fill(name)
  const lost = await hold(page, '**/api/v1/admin/tags', 'POST', true)
  try {
    await page.getByTestId('tags-submit').click()
    expect(await lost.started).toBe(201)
    await expect(page.getByTestId('tags-submit')).toBeEnabled({ timeout: 18_000 })
    await expect(section.getByRole('alert')).toContainText('保存结果尚未确认')
  }
  finally { await lost.cleanup() }
  // A late success must not clear the retained form or replay the write.
  await expect(page.getByTestId('tags-name')).toHaveValue(name)
  const committed = await (await page.request.get('/api/v1/admin/tags')).json()
  expect(committed.filter((item: { slug: string }) => item.slug === name)).toHaveLength(1)
  const read = await hold(page, '**/api/v1/admin/tags', 'GET')
  try {
    await section.getByRole('button', { name: '核对最新列表' }).click()
    await read.started
    await expect(section.getByRole('button', { name: '核对最新列表' })).toBeEnabled({ timeout: 18_000 })
    await expect(section.getByRole('alert')).toContainText('核对超时')
    await expect(page.getByTestId('tags-name')).toHaveValue(name)
  }
  finally { await read.cleanup() }
  await section.getByRole('button', { name: '核对最新列表' }).click()
  await expect(section.locator('.taxonomy-manager__row').filter({ hasText: name })).toHaveCount(1)
  await expect(section.getByRole('status')).toContainText('列表已更新')
  await expect(page.getByTestId('tags-name')).toHaveValue(name)
  expect(writes).toBe(1)
})

test('taxonomy stalled updates and deletes retain state and recover through explicit actions', async ({ page }) => {
  test.setTimeout(110_000)
  const headers = await openTaxonomy(page)
  const name = `existing-${Date.now()}`
  const created = await page.request.post('/api/v1/admin/tags', { headers, data: { name, slug: name } })
  expect(created.status()).toBe(201)
  const item = await created.json() as { id: number }
  await page.reload()
  await expectHydrated(page)
  const section = page.getByTestId('taxonomy-tags')
  const row = section.locator('.taxonomy-manager__row').filter({ hasText: name })
  await row.getByRole('button', { name: '编辑', exact: true }).click()
  await page.getByTestId('tags-name').fill(`${name}-changed`)
  const update = await hold(page, `**/api/v1/admin/tags/${item.id}`, 'PATCH')
  try {
    await page.getByTestId('tags-submit').click()
    await update.started
    await expect(page.getByTestId('tags-submit')).toBeEnabled({ timeout: 18_000 })
    await expect(section.getByRole('alert')).toContainText('保存结果尚未确认')
    await expect(page.getByTestId('tags-name')).toHaveValue(`${name}-changed`)
    expect(update.count()).toBe(1)
  }
  finally { await update.cleanup() }
  const removal = await hold(page, `**/api/v1/admin/tags/${item.id}`, 'DELETE')
  try {
    page.once('dialog', dialog => dialog.accept())
    await row.getByRole('button', { name: '删除', exact: true }).click()
    await removal.started
    await expect(row.getByRole('button', { name: '删除', exact: true })).toBeEnabled({ timeout: 18_000 })
    await expect(section.getByRole('alert')).toContainText('删除结果尚未确认')
    await expect(row).toBeVisible()
    await expect(page.getByTestId('tags-name')).toHaveValue(`${name}-changed`)
    expect(removal.count()).toBe(1)
  }
  finally { await removal.cleanup() }
  await section.getByRole('button', { name: '核对最新列表' }).click()
  await expect(section.getByRole('status')).toContainText('列表已更新')
  page.once('dialog', dialog => dialog.accept())
  await row.getByRole('button', { name: '删除', exact: true }).click()
  await expect(row).toHaveCount(0)
  await page.reload()
  await expectHydrated(page)
  await expect(page.getByTestId('taxonomy-tags')).not.toContainText(name)
})
