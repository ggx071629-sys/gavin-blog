import { expect, test } from '@playwright/test'
import { resolveE2EWebPort } from '../support/e2e-env'
import { expectHydrated } from '../support/hydration'

const webPort = resolveE2EWebPort()

test('login stays same-origin on localhost and loopback hosts', async ({ browser }) => {
  for (const hostname of ['localhost', '127.0.0.1']) {
    const context = await browser.newContext()
    const page = await context.newPage()
    const origin = `http://${hostname}:${webPort}`

    await page.goto(`${origin}/admin/login`, { waitUntil: 'domcontentloaded' })
    await expectHydrated(page)
    await page.getByTestId('username').fill('gavin')
    await page.getByTestId('password').fill('intentionally-wrong')

    const loginResponse = page.waitForResponse(response =>
      response.request().method() === 'POST'
      && response.url() === `${origin}/api/v1/auth/login`,
    )
    await page.getByTestId('login').click()

    expect((await loginResponse).status()).toBe(401)
    await expect(page.getByRole('alert')).toHaveText('用户名或密码不正确。')
    await context.close()
  }
})
