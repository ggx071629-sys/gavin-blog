import { spawn } from 'node:child_process'
import { mkdtemp, readFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { expect, test, type BrowserContext, type Page } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

test('real HTTP password change recovery and revocation', async ({ page, browser }) => {
  const root = await mkdtemp(join(tmpdir(), 'account-flow-'))
  const api = 'http://127.0.0.1:8191'
  const apiRoot = resolve('../api')
  const python = join(apiRoot, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python')
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.toUpperCase().startsWith('GAVIN_')))
  const child = spawn(python, ['scripts/run_account_fixture.py', '--root', root, '--port', '8191'], { cwd: apiRoot, env, windowsHide: true, stdio: 'ignore' })
  let spawnError: Error | undefined
  child.on('error', error => { spawnError = error })
  const exited = new Promise<void>(resolveExit => child.once('exit', () => resolveExit()))
  const other = await browser.newContext()
  // Transport-only proxy to an actual isolated HTTP API. No synthetic auth response.
  const proxy = async (context: BrowserContext) => context.route('**/api/v1/**', async (route) => {
    const response = await route.fetch({ url: api + new URL(route.request().url()).pathname, maxRetries: 0 })
    await route.fulfill({ response })
  })
  const login = async (target: Page, password: string) => {
    await target.goto('/admin/login')
    await expectHydrated(target)
    await target.getByTestId('username').fill('gavin')
    await target.getByTestId('password').fill(password)
    await target.getByTestId('login').click()
    await expect(target).toHaveURL(/\/admin\/articles$/)
  }
  const fill = async (password: string, code: string) => {
    await page.getByLabel('新密码', { exact: true }).fill(password)
    await page.getByLabel('确认新密码', { exact: true }).fill(password)
    await page.getByLabel('邮箱验证码').fill(code)
  }
  const confirm = async (label: string) => {
    await page.getByRole('button', { name: label, exact: true }).click()
    await page.getByRole('button', { name: '确认更新密码', exact: true }).click()
  }
  try {
    await expect.poll(async () => {
      if (spawnError) throw spawnError
      return await page.request.get(api + '/api/health').then(r => r.status()).catch(() => 0)
    }, { timeout: 30_000 }).toBe(200)
    await proxy(page.context())
    await proxy(other)
    const otherPage = await other.newPage()
    await login(page, 'correct-horse')
    await login(otherPage, 'correct-horse')
    await page.getByRole('link', { name: '账号安全', exact: true }).click()
    await expect(page.getByTestId('account-email')).toHaveText('f***@example.invalid')
    await page.getByLabel('当前密码', { exact: true }).fill('wrong-password')
    await page.getByRole('button', { name: '发送验证码', exact: true }).click()
    await expect(page.getByRole('alert')).toContainText('当前密码不正确')
    await page.getByLabel('当前密码', { exact: true }).fill('correct-horse')
    await page.getByRole('button', { name: '发送验证码', exact: true }).click()
    await expect(page.getByRole('status').filter({ hasText: '已提交发送' })).toBeVisible()
    const changeCode = JSON.parse(await readFile(join(root, 'change.json'), 'utf8')).code
    await fill('account-changed-password-2026', changeCode === '000000' ? '111111' : '000000')
    await confirm('修改密码')
    await expect(page.getByRole('alert')).toContainText('验证码错误')
    await page.getByLabel('邮箱验证码').fill(changeCode)
    await confirm('修改密码')
    await expect(page).toHaveURL(/password-updated/)
    expect((await other.request.get(api + '/api/v1/auth/session')).status()).toBe(401)
    expect((await page.request.get(api + '/api/v1/auth/session')).status()).toBe(401)
    await login(page, 'account-changed-password-2026')
    await login(otherPage, 'account-changed-password-2026')
    await page.getByRole('link', { name: '账号安全', exact: true }).click()
    await page.getByRole('link', { name: '忘记密码', exact: true }).click()
    await page.getByRole('button', { name: '发送验证码', exact: true }).click()
    await expect(page.getByRole('status')).toContainText('已提交发送')
    const recoveryCode = JSON.parse(await readFile(join(root, 'recovery.json'), 'utf8')).code
    await fill('account-recovered-password-2026', recoveryCode)
    await confirm('重设密码')
    await expect(page).toHaveURL(/password-updated/)
    expect((await other.request.get(api + '/api/v1/auth/session')).status()).toBe(401)
    await login(page, 'account-recovered-password-2026')
    // The account-wide send reservation survives both password changes.
    await page.getByRole('link', { name: '账号安全', exact: true }).click()
    await page.getByLabel('当前密码', { exact: true }).fill('account-recovered-password-2026')
    await page.getByRole('button', { name: '发送验证码', exact: true }).click()
    // Same-purpose cooldown is intentionally server-enforced even after a password change.
    await expect(page.getByRole('alert')).toContainText('操作过于频繁')
    await expect(page.getByRole('button', { name: '修改密码', exact: true })).toBeDisabled()
  }
  finally {
    await other.close()
    await page.context().unrouteAll({ behavior: 'wait' })
    if (child.exitCode === null) child.kill()
    await exited
    await rm(root, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 })
  }
})
