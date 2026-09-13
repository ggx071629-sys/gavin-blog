import { expect, type Page } from '@playwright/test'

export const HYDRATION_TIMEOUT_MS = 30_000

export const expectHydrated = (page: Page) => expect(page.getByTestId('app-root'))
  .toHaveAttribute('data-hydrated', 'true', { timeout: HYDRATION_TIMEOUT_MS })
