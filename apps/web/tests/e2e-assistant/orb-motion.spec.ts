import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

test('assistant orb motion pauses accessibly and cleans up across preferences and navigation', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  page.on('console', message => {
    // Entering the protected writing desk intentionally redirects an anonymous user.
    if (message.location().url.endsWith('/api/v1/auth/session') && message.text().includes('401 (Unauthorized)')) return
    if (['error', 'warning'].includes(message.type())) errors.push(message.text())
  })
  let requests = 0
  page.on('request', request => { if (request.url().includes('/api/v1/assistant/') && !request.url().endsWith('/availability')) requests++ })
  await page.addInitScript(() => localStorage.setItem('gavin:assistant-orb-guidance:v1', '1'))
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.emulateMedia({ reducedMotion: 'no-preference' })
  await page.goto('/about')
  await expectHydrated(page)
  const orb = page.getByTestId('assistant-orb')
  const orbit = page.locator('.assistant-orb-orbit')
  const rotor = page.locator('.assistant-orb-scroll')
  const transform = () => orbit.evaluate(el => (el as HTMLElement).style.transform)
  await expect.poll(transform).not.toBe('')
  const initial = await transform()
  await expect.poll(transform).not.toBe(initial)
  // Scroll feedback uses the real document extent, including late layout changes.
  const rotation = await rotor.evaluate(el => (el as HTMLElement).style.transform)
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight))
  await expect.poll(() => rotor.evaluate(el => (el as HTMLElement).style.transform)).not.toBe(rotation)
  await orb.focus()
  const focused = await transform()
  await page.waitForTimeout(350)
  expect(await transform()).toBe(focused)
  const pause = page.getByRole('button', { name: '暂停悬浮球动效' })
  await pause.click()
  await expect(page.getByRole('button', { name: '播放悬浮球动效' })).toHaveAttribute('aria-pressed', 'true')
  await expect.poll(transform).toBe('')
  await page.reload()
  await expectHydrated(page)
  await expect(page.getByRole('button', { name: '播放悬浮球动效' })).toBeVisible()
  await page.waitForTimeout(350)
  expect(await transform()).toBe('')
  await page.getByRole('button', { name: '播放悬浮球动效' }).click()
  await expect.poll(transform).not.toBe('')
  await page.evaluate(() => {
    Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'hidden' })
    document.dispatchEvent(new Event('visibilitychange'))
  })
  await expect.poll(transform).toBe('')
  await page.evaluate(() => {
    delete (document as unknown as Record<string, unknown>).visibilityState
    document.dispatchEvent(new Event('visibilitychange'))
  })
  await expect.poll(transform).not.toBe('')
  // Lifecycle: the same detached nodes must be reverted and receive no later writes.
  for (let index = 0; index < 2; index++) {
    const detached = await orbit.elementHandle()
    await page.getByRole('link', { name: '写作台', exact: true }).first().click()
    await expect(orb).toHaveCount(0)
    await page.waitForTimeout(350)
    expect(await detached!.evaluate(el => ({ connected: el.isConnected, transform: (el as HTMLElement).style.transform }))).toEqual({ connected: false, transform: '' })
    await page.goBack()
    await expect(orb).toBeVisible()
    await expect(orbit).toHaveCount(1)
    await expect.poll(transform).not.toBe('')
    await detached!.dispose()
  }
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await expect.poll(transform).toBe('')
  await expect(pause).toBeHidden()
  const still = await transform()
  await page.waitForTimeout(350)
  expect(await transform()).toBe(still)
  for (const width of [320, 390, 640, 1280]) {
    await page.setViewportSize({ width, height: 700 })
    await expect(orb).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  }
  const accessibility = await new AxeBuilder({ page }).include('.assistant-orb-layer').analyze()
  expect(accessibility.violations).toEqual([])
  await page.emulateMedia({ reducedMotion: 'no-preference' })
  await page.setViewportSize({ width: 390, height: 844 })
  await expect.poll(transform).not.toBe('')
  await page.evaluate(() => { document.documentElement.classList.remove('light'); document.documentElement.classList.add('dark') })
  expect((await new AxeBuilder({ page }).include('.assistant-orb-layer').analyze()).violations).toEqual([])
  expect(requests).toBe(0)
  expect(errors).toEqual([])
})
