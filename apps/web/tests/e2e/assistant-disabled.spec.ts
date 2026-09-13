import { expect, test } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

test('disabled assistant flag never mounts a launcher or assistant API traffic', async ({ page }) => {
  const assistantRequests: string[] = []
  page.on('request', (request) => {
    if (request.url().includes('/api/v1/assistant')) assistantRequests.push(request.url())
  })
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await expectHydrated(page)
  await expect(page.getByTestId('assistant-launcher')).toHaveCount(0)
  await expect(page.getByTestId('assistant-orb')).toHaveCount(0)
  await expect(page.getByTestId('assistant-orb-hint')).toHaveCount(0)
  await expect(page.getByTestId('assistant-panel')).toHaveCount(0)
  expect(assistantRequests).toEqual([])
})
