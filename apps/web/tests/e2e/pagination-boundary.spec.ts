import { expect, test } from '@playwright/test'
import { expectHydrated as waitForHydration } from '../support/hydration'

test('public pagination canonicalizes oversized and invalid page query values by page size', async ({ page }) => {
  await page.goto('/projects?page=999999', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  await expect(page).toHaveURL(/\/projects\?page=8334$/)

  await page.goto('/archive?page=999999', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  await expect(page).toHaveURL(/\/archive\?page=5001$/)

  await page.goto('/projects?page=invalid', { waitUntil: 'domcontentloaded' })
  await waitForHydration(page)
  await expect(page).toHaveURL(/\/projects$/)
})
