import AxeBuilder from '@axe-core/playwright'
import { join } from 'node:path'
import { expect, test } from '@playwright/test'
import { expectHydrated } from '../support/hydration'

test('management real trial budget public switch and responsive maintenance', async ({ page }, info) => {
  test.setTimeout(180000)
  await page.goto('/admin/login')
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  await page.goto('/admin/assistant')
  await expectHydrated(page)
  await expect(page.getByRole('heading', { name: '问答助手管理' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '已向访客开放' })).toBeVisible()
  await page.getByRole('button', { name: '关闭对外问答', exact: true }).click()
  await page.getByRole('dialog').getByRole('button', { name: '关闭对外问答' }).click()
  await expect(page.getByRole('heading', { name: '已关闭对外问答' })).toBeVisible()
  const visitorContext = await page.context().browser()!.newContext()
  const visitor = await visitorContext.newPage()
  await visitor.goto('/')
  await expectHydrated(visitor)
  await expect(visitor.getByTestId('assistant-launcher')).toHaveCount(0)
  await visitorContext.close()

  await page.getByRole('link', { name: '高级维护' }).click()
  await expect(page.getByRole('heading', { name: '高级维护', exact: true })).toBeVisible()
  const resume = page.getByRole('button', { name: '恢复后台试问' })
  if (await resume.isVisible()) { await resume.click(); await expect(resume).toBeHidden() }
  await page.getByRole('button', { name: '关闭弹窗' }).click()
  await page.getByRole('navigation', { name: '助手管理视图' }).getByRole('link', { name: '试问', exact: true }).click()
  await expect(page.locator('.am-trial-empty')).toBeVisible()
  await page.screenshot({ path: join(info.project.outputDir, 'trial', 'empty.png'), fullPage: true })
  // Unavailable trial must block keyboard submission as well as the disabled button.
  await page.route('**/api/v1/admin/assistant/management', async route => {
    const response = await route.fetch()
    await route.fulfill({ response, json: { ...await response.json(), trial_available: false } })
  })
  await page.getByRole('button', { name: '刷新状态' }).click()
  await expect(page.getByText('当前试问条件尚未满足', { exact: false })).toBeVisible()
  let submissions = 0
  const countSubmission = (request: import('@playwright/test').Request) => {
    if (request.url().endsWith('/trial/sessions') && request.method() === 'POST') submissions++
  }
  page.on('request', countSubmission)
  await page.getByLabel('你的问题').fill('blocked shortcut')
  await expect(page.getByRole('button', { name: '发送问题' })).toBeDisabled()
  await page.getByLabel('你的问题').press('Control+Enter')
  await page.getByLabel('你的问题').press('Meta+Enter')
  await page.getByRole('button', { name: '刷新状态' }).click()
  await expect(page.getByRole('button', { name: '刷新状态' })).toBeEnabled()
  expect(submissions).toBe(0)
  page.off('request', countSubmission)
  await page.unroute('**/api/v1/admin/assistant/management')
  await page.getByRole('button', { name: '刷新状态' }).click()
  await expect(page.getByRole('button', { name: '发送问题' })).toBeEnabled()
  await page.getByLabel('你的问题').fill('Which published notes cover FastAPI?')
  await page.getByRole('button', { name: '发送问题' }).click()
  await expect(page.locator('.am-answer').first()).toContainText('FastAPI', { timeout: 30000 })
  const originalAnswer = await page.locator('.am-answer').first().innerText()
  await expect(page.locator('.am-turn small')).not.toContainText('待结算', { timeout: 10000 })
  await expect(page.locator('.am-source')).toBeHidden()
  await page.getByText('查看回答依据（1 处）').click()
  await expect(page.locator('.am-source blockquote')).not.toBeEmpty()
  await expect(page.locator('.am-source a')).toHaveAttribute('href', /^\/(?:notes\/|$)/)
  await page.reload()
  await expectHydrated(page)
  await expect(page.locator('.am-answer').first()).toHaveText(originalAnswer)
  await expect(page.locator('.am-source')).toBeHidden()
  for (const theme of ['light', 'dark']) {
    await page.setViewportSize({ width: 1440, height: 900 })
    if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== (theme === 'dark')) await page.getByRole('button', { name: '切换颜色主题' }).click()
    for (const width of [320, 390, 1440]) {
      await page.setViewportSize({ width, height: 900 })
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1)
      expect((await new AxeBuilder({ page }).include('.am-trial').withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()).violations).toEqual([])
      await page.screenshot({ path: join(info.project.outputDir, 'trial', `${theme[0]}${width}.png`), fullPage: true })
    }
  }
  await page.getByRole('button', { name: '清空试问' }).click()
  await expect(page.locator('.am-turn')).toHaveCount(0)
  await page.getByRole('navigation', { name: '助手管理视图' }).getByRole('link', { name: '概览' }).click()
  await page.getByRole('button', { name: '修改预算', exact: true }).click()
  const budget = page.getByRole('dialog')
  await expect(budget).toBeVisible()
  await page.getByLabel('每日总预算（元）').fill('0')
  await budget.getByRole('button', { name: '保存预算' }).click()
  await expect(budget).toBeHidden()
  await expect(page.getByText('剩余预算不足以开始一次问答')).toBeVisible()
  await page.getByRole('button', { name: '修改预算', exact: true }).last().click()
  await page.getByLabel('每日总预算（元）').fill('1')
  await page.getByRole('dialog').getByRole('button', { name: '保存预算' }).click()
  await expect(page.getByRole('dialog')).toBeHidden()

  for (const theme of ['light', 'dark']) {
    if (await page.locator('html').evaluate(el => el.classList.contains('dark')) !== (theme === 'dark')) await page.getByRole('button', { name: '切换颜色主题' }).click()
    for (const width of [320, 390, 1440]) {
      await page.setViewportSize({ width, height: 900 })
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1)
      // Keep exported Windows paths bounded; each Harness batch owns outputDir.
      await page.screenshot({ path: join(info.project.outputDir, 'management', `${theme}-${width}.png`), fullPage: true })
    }
    const axe = await new AxeBuilder({ page }).include('.assistant-management').withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
    expect(axe.violations).toEqual([])
  }
  await page.getByRole('button', { name: '向访客开放', exact: true }).click()
  await page.getByRole('dialog').getByRole('button', { name: '向访客开放' }).click()
  await expect(page.getByRole('heading', { name: '已向访客开放' })).toBeVisible()
})
