import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import type { AssistantSessionTurn } from '../../types/api'
import { expectHydrated } from '../support/hydration'

const policy = { question_max_chars: 500, session_idle_seconds: 1800, session_absolute_seconds: 14400, body_retention_seconds: 1800 }
const source = { n: '1', title: '隔离审查来源：Python 与 FastAPI', path: '/notes/2026/08/python-notes' }
const answer = (id: string, body = '本站的公开笔记介绍 FastAPI。[1] 再次核对原文。[1]'): AssistantSessionTurn => ({
  turn_id: id, created_at: '2026-09-06T00:00:00Z', status: 'answer', code: 'answered', message: 'ok',
  question: `隔离问题 ${id}`, answer: body, citations: [source], sources: [source], body_available: true,
})
const fixture = async (page: Page, initial: AssistantSessionTurn[] = []) => {
  const state = { feedbackCalls: 0, feedbackFail: false, feedbackHold: null as Promise<void> | null, turns: initial, code: '', status: 429, posts: 0, gets: 0, deletes: 0, deleteStatus: 204, hold: null as Promise<void> | null, badCitation: false, disconnected: false, multipleChunks: false }
  await page.route('**/api/v1/assistant/**', async route => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/feedback')) {
      state.feedbackCalls++
      expect(Object.keys(route.request().postDataJSON())).toEqual(['value'])
      const turnId = path.split('/').at(-2)
      const turn = state.turns.find(item => item.turn_id === turnId)
      if (state.feedbackHold) await state.feedbackHold
      if (state.feedbackFail) return route.fulfill({ status: 503, json: { error: { code: 'assistant_not_ready', message: 'unavailable' } } })
      const value = route.request().postDataJSON().value
      if (turn) turn.feedback = value
      return route.fulfill({ json: { turn_id: turnId, value } })
    }
    if (path.endsWith('/availability')) return route.fulfill({ json: { available: true } })
    if (path.endsWith('/sessions')) return route.fulfill({ json: { policy } })
    if (route.request().method() === 'DELETE') {
      state.deletes++
      if (state.hold) await state.hold
      if (state.deleteStatus === 503) return route.fulfill({ status: 503, json: { detail: 'content writes are temporarily fenced' } })
      state.turns = []
      if (state.deleteStatus === 0) return route.abort()
      return route.fulfill(state.deleteStatus === 204 ? { status: 204 } : { status: 202, json: { error: { code: 'session_revoking', message: 'pending' } } })
    }
    if (path.endsWith('/session')) {
      state.gets++
      return route.fulfill({ json: { session_id: 'isolated', created_at: '2026-09-06', idle_expires_at: '2026-09-07', absolute_expires_at: '2026-09-07', policy, turns: state.turns, active_turn: null } })
    }
    state.posts++
    if (state.hold) await state.hold
    if (state.disconnected) return route.abort()
    const code = state.code
    if (code && !['insufficient_evidence', 'out_of_scope', 'prompt_blocked', 'clarification_required', 'completeness_unverified', 'freshness_unverified'].includes(code)) {
      return route.fulfill({ status: state.status, headers: { 'Retry-After': '3' }, json: { error: { code, message: 'isolated failure' } } })
    }
    const turn = answer(`reply-${state.posts}`)
    if (state.multipleChunks) {
      turn.answer = '证书申请。[1] 自动续期。[2]'
      turn.citations = [source, { ...source, n: '2', heading_path: '自动续期' }]
    }
    turn.question = route.request().postDataJSON().question
    const event = code ? 'refusal' : 'answer'
    if (code) Object.assign(turn, { status: event, code, answer: null, citations: null, sources: null })
    state.turns.push(turn)
    const payload = { event_id: 2, turn_id: turn.turn_id, type: event, code: code || 'answered', message: 'ok', ...(!code ? { answer: state.badCitation ? '不得显示的答案[99]' : turn.answer, citations: turn.citations, sources: turn.sources } : {}) }
    const stage = { event_id: 1, turn_id: turn.turn_id, stage: 'validating' }
    return route.fulfill({ contentType: 'text/event-stream', body: `id: 1\nevent: validating\ndata: ${JSON.stringify(stage)}\n\nid: 2\nevent: ${event}\ndata: ${JSON.stringify(payload)}\n\n` })
  })
  await page.goto('/')
  await expectHydrated(page)
  expect(state.gets).toBe(0)
  await page.getByTestId('assistant-launcher').click()
  await expect(page.getByLabel('问题', { exact: true })).toBeEnabled()
  return state
}
const submit = async (page: Page, text = '请依据本站公开内容回答') => {
  await page.getByLabel('问题', { exact: true }).fill(text)
  await page.getByRole('button', { name: '发送', exact: true }).click()
}

test('clarification is a distinct recoverable terminal notice', async ({ page }) => {
  const state = await fixture(page)
  state.code = 'clarification_required'
  await submit(page, '第二个项目用了什么？')
  await expect(page.getByText('需要明确对象', { exact: true })).toBeVisible()
  await expect(page.getByTestId('assistant-answer')).toHaveCount(0)
  await expect(page.getByText('证据不足', { exact: true })).toHaveCount(0)
  await expect(page.getByRole('button', { name: '发送', exact: true })).toBeDisabled()
  await page.reload()
  await expectHydrated(page)
  await page.getByTestId('assistant-launcher').click()
  await expect(page.getByText('需要明确对象', { exact: true })).toBeVisible()
  expect(state.posts).toBe(1)
  await page.getByLabel('问题', { exact: true }).fill('Python notes介绍什么？')
  await expect(page.getByRole('button', { name: '发送', exact: true })).toBeEnabled()
})

test('unverified completeness and freshness remain distinct after restore', async ({ page }) => {
  const state = await fixture(page)
  for (const [code, title] of [['completeness_unverified', '完整性尚未核验'], ['freshness_unverified', '时效尚未核验']]) {
    state.code = code!
    await submit(page, code === 'completeness_unverified' ? '列出全部项目' : '最新文章是哪篇？')
    await expect(page.getByText(title!, { exact: true })).toBeVisible()
    await page.reload()
    await expectHydrated(page)
    await page.getByTestId('assistant-launcher').click()
    await expect(page.getByText(title!, { exact: true })).toBeVisible()
    await expect(page.getByText('证据不足', { exact: true })).toHaveCount(0)
    await expect(page.getByTestId('assistant-answer')).toHaveCount(0)
  }
  expect(state.posts).toBe(2)
})

test('teleported assistant cards share public focus feedback', async ({ page }) => {
  await fixture(page)
  const welcome = page.locator('.assistant-welcome-card')
  await welcome.hover()
  await expect.poll(() => welcome.evaluate(el => getComputedStyle(el, '::after').opacity)).toBe('1')
  await submit(page)
  const sourceCard = page.locator('.assistant-source-row').first()
  await sourceCard.scrollIntoViewIfNeeded()
  const before = await sourceCard.boundingBox()
  await sourceCard.focus()
  await page.keyboard.press('Tab')
  await expect(sourceCard.locator('a')).toBeFocused()
  await expect.poll(() => sourceCard.evaluate(el => getComputedStyle(el, '::after').opacity)).toBe('1')
  expect(await sourceCard.boundingBox()).toEqual(before)
  expect(await sourceCard.evaluate(el => getComputedStyle(el, '::after').pointerEvents)).toBe('none')
  expect(await sourceCard.evaluate(el => getComputedStyle(el, '::after').transitionDuration)).toBe('0s')
  await sourceCard.locator('a').click()
  await expect(page).toHaveURL(new RegExp(`${source.path}$`))
  await expect(page.locator('.assistant-dialog')).toHaveCount(0)
})

test('multiple chunk citations navigate the deduplicated source live and after reload', async ({ page }) => {
  const state = await fixture(page)
  state.multipleChunks = true
  await submit(page)
  for (const restored of [false, true]) {
    if (restored) {
      await page.reload()
      await expectHydrated(page)
      await page.getByTestId('assistant-launcher').click()
    }
    await expect(page.getByTestId('assistant-answer')).toContainText('自动续期。')
    await expect(page.locator('.assistant-source-row')).toHaveCount(2)
    const marker = page.getByRole('button', { name: '查看来源 2', exact: true })
    await marker.click()
    await expect(page.locator('.assistant-source-row').nth(1)).toBeFocused()
    await page.getByRole('button', { name: '返回引用' }).click()
    await expect(marker).toBeFocused()
  }
  expect(state.posts).toBe(1)
})

test('panel layout', async ({ page }, info) => {
  const longTurn = answer('long', ('长回答与来源需要保持阅读宽度。[1]\n\n').repeat(20))
  longTurn.sources![0] = { ...source, title: '隔离审查长来源标题'.repeat(30) }
  longTurn.citations = longTurn.sources
  await fixture(page, [longTurn])
  for (const theme of ['light', 'dark']) {
    await page.evaluate(theme => { document.documentElement.classList.toggle('dark', theme === 'dark'); document.documentElement.classList.toggle('light', theme === 'light') }, theme)
    for (const width of [320, 390, 639, 640, 1024, 1279, 1280, 1440]) {
      await page.setViewportSize({ width, height: 844 })
      const dialog = page.getByRole('dialog', { name: '问 Gavin' })
      const box = await dialog.boundingBox()
      expect(box!.width).toBeCloseTo(width < 640 ? width : 480, 0)
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      if (width < 1280) await expect(dialog).toHaveAttribute('aria-modal', 'true')
      else await expect(dialog).not.toHaveAttribute('aria-modal')
      await expect(page.getByRole('button', { name: '发送', exact: true })).toBeInViewport()
      if ([390, 1024, 1440].includes(width)) await page.screenshot({ path: info.outputPath(`${theme}-${width}.png`) })
    }
    await page.setViewportSize({ width: 390, height: 480 })
    await page.getByLabel('问题', { exact: true }).fill('长问题'.repeat(160))
    expect(await page.locator('.assistant-input').evaluate(el => el.clientHeight)).toBeLessThanOrEqual(120)
    await expect(page.getByRole('button', { name: '发送', exact: true })).toBeInViewport()
    await page.getByRole('button', { name: '范围与数据说明' }).click()
    await page.getByRole('button', { name: '清除对话', exact: true }).click()
    await expect(page.getByRole('button', { name: '取消', exact: true })).toBeFocused()
    await expect(page.getByRole('button', { name: '确认清除' })).toBeInViewport()
    await page.keyboard.press('Escape')
    await expect(page.getByRole('button', { name: '清除对话', exact: true })).toBeFocused()
    await page.setViewportSize({ width: 390, height: 844 })
    await page.evaluate(() => {
      Object.defineProperty(window.visualViewport, 'height', { configurable: true, value: 380 })
      Object.defineProperty(window.visualViewport, 'offsetTop', { configurable: true, value: 30 })
      window.visualViewport!.dispatchEvent(new Event('resize'))
    })
    const keyboardBox = await page.getByRole('dialog', { name: '问 Gavin' }).boundingBox()
    expect(keyboardBox!.height).toBeCloseTo(380, 0)
    expect(keyboardBox!.y).toBeCloseTo(30, 0)
    await expect(page.getByRole('button', { name: '发送', exact: true })).toBeInViewport()
    await page.evaluate(() => { delete (window.visualViewport as unknown as Record<string, unknown>).height; delete (window.visualViewport as unknown as Record<string, unknown>).offsetTop; window.visualViewport!.dispatchEvent(new Event('resize')) })
    await page.getByRole('button', { name: '范围与数据说明' }).click()
    const axe = await new AxeBuilder({ page }).include('#ask-gavin-panel').analyze()
    expect(axe.violations).toEqual([])
  }
  await page.emulateMedia({ reducedMotion: 'reduce' })
  expect(await page.locator('.assistant-dialog').evaluate(el => getComputedStyle(el).animationName)).toBe('none')
})

test('panel interaction', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  const state = await fixture(page)
  await expect(page.getByText('已恢复 0 轮')).toHaveCount(0)
  await expect(page.locator('#assistant-data-policy')).toBeVisible()
  await page.locator('.assistant-example').first().click()
  expect(state.posts).toBe(0)
  const input = page.getByLabel('问题', { exact: true })
  await input.fill('')
  await input.fill('界'.repeat(501))
  await expect(input).toHaveValue('')
  await input.fill('输入法测试')
  await input.dispatchEvent('compositionstart')
  await input.press('Enter')
  expect(state.posts).toBe(0)
  await input.dispatchEvent('compositionend')
  await input.fill('输入法提交后仍需确认')
  await input.press('Shift+Enter')
  expect(state.posts).toBe(0)
  await input.press('Enter')
  await expect(page.getByTestId('assistant-answer')).toBeVisible()
  await expect(page.locator('.assistant-welcome')).toHaveCount(0)
  await expect(page.locator('#assistant-data-policy')).toHaveCount(0)
  const citation = page.getByRole('button', { name: '查看来源 1' }).nth(1)
  await citation.click()
  await expect(page.locator('.assistant-source-row')).toBeFocused()
  await page.getByRole('button', { name: '返回引用' }).click()
  await expect(citation).toBeFocused()
  await page.locator('.assistant-source-link').click()
  await expect(page).toHaveURL(/python-notes$/)
  await expect(page.locator('#main-content')).toBeFocused()
  await page.getByTestId('assistant-launcher').click()
  await page.locator('.assistant-source-link').click()
  await expect(page.locator('#main-content')).toBeFocused()
  await expect(page.getByRole('dialog')).toBeHidden()
  // Restore a long history, then deliver a delayed answer while the reader is above it.
  state.turns = Array.from({ length: 4 }, (_, i) => answer(`history-${i}`, ('长记录。[1]\n\n').repeat(12)))
  await page.reload(); await expectHydrated(page); await page.getByTestId('assistant-launcher').click()
  await expect(page.getByText('已恢复 4 轮', { exact: true })).toBeVisible()
  let release!: () => void
  state.hold = new Promise<void>(resolve => { release = resolve })
  await submit(page, '等待中保留本次问题')
  await expect(page.getByText('等待中保留本次问题', { exact: true })).toBeVisible()
  const log = page.getByRole('log')
  await log.evaluate(el => { el.scrollTop = 100; el.dispatchEvent(new Event('scroll')) })
  const before = await log.evaluate(el => el.scrollTop)
  release()
  await expect(page.locator('.assistant-turn')).toHaveCount(5)
  expect(await log.evaluate(el => el.scrollTop)).toBe(before)
  await page.getByRole('button', { name: '查看新回复' }).click()
  await expect.poll(() => log.evaluate(el => el.scrollTop)).toBeGreaterThan(before)
  await expect(page.locator('.assistant-turn').last()).toBeInViewport()
  await page.setViewportSize({ width: 390, height: 844 })
  await input.fill('手机换行')
  await input.press('Enter')
  await expect(input).toHaveValue('手机换行\n')
  expect(state.posts).toBe(2)
})

test('panel state recovery', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  const state = await fixture(page)
  for (const code of ['insufficient_evidence', 'out_of_scope', 'prompt_blocked']) {
    state.code = code
    await submit(page, `隔离拒答 ${code}`)
    await expect(page.locator('.assistant-turn').last()).toContainText(code === 'insufficient_evidence' ? '证据不足' : '超出回答范围')
    await expect(page.locator('.assistant-turn').last()).toContainText(`隔离拒答 ${code}`)
  }
  await page.getByRole('link', { name: '搜索本站', exact: true }).click()
  await expect(page).toHaveURL(/\/search$/)
  await page.getByTestId('assistant-launcher').click()
  for (const code of ['rate_limited', 'concurrency_limited', 'stream_connection_limited', 'provider_result_unknown']) {
    state.code = code
    await submit(page, `隔离故障 ${code}`)
    await expect(page.getByRole('button', { name: '检查结果' })).toBeVisible()
    await expect(page.locator('.assistant-pending')).toContainText(`隔离故障 ${code}`)
    const posts = state.posts
    await page.getByRole('button', { name: '检查结果' }).click()
    await expect(page.getByLabel('问题', { exact: true })).toBeEnabled()
    expect(state.posts).toBe(posts)
  }
  for (const code of ['assistant_session_expired', 'csrf_failed', 'budget_exhausted', 'assistant_disabled', 'assistant_not_ready', 'origin_rejected']) {
    state.code = code
    await submit(page, `隔离不可用 ${code}`)
    await expect(page.getByLabel('问题', { exact: true })).toBeDisabled()
    if (code === 'assistant_session_expired') await page.getByRole('button', { name: '重新开始' }).click()
    else if (code === 'csrf_failed') await page.getByRole('button', { name: '重新同步' }).click()
    else { await page.reload(); await expectHydrated(page); await page.getByTestId('assistant-launcher').click() }
    await expect(page.getByLabel('问题', { exact: true })).toBeEnabled()
  }
  state.code = ''; state.badCitation = true
  await submit(page)
  await expect(page.getByText('来源无法校验，已隐藏这份答案。')).toBeVisible()
  await expect(page.getByText('不得显示的答案[99]', { exact: true })).toHaveCount(0)
  state.badCitation = false
  // A real browser transport abort exhausts same-key reconnects, then reads status.
  state.disconnected = true
  await submit(page, '断线的本次问题')
  await expect(page.getByText('正在完成上一个问题', { exact: true })).toBeVisible()
  await expect(page.locator('.assistant-pending')).toContainText('断线的本次问题')
  await expect(page.getByLabel('问题', { exact: true })).toBeEnabled({ timeout: 15000 })
  state.disconnected = false
  for (const status of [204, 202, 0]) {
    state.deleteStatus = status
    let release!: () => void
    state.hold = new Promise<void>(resolve => { release = resolve })
    await page.getByRole('button', { name: '清除对话', exact: true }).click()
    await page.getByRole('button', { name: '确认清除' }).click()
    await expect(page.getByText('正在清除旧会话', { exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: '清除对话', exact: true })).toBeDisabled()
    release(); state.hold = null
    await expect(page.getByText(status === 204 ? '本站可读问答已清除' : status === 202 ? '正在清除旧会话' : '未能确认清除完成', { exact: true })).toBeVisible()
    state.deleteStatus = 204
    await page.getByRole('button', { name: '重新开始' }).click()
    await expect(page.getByLabel('问题', { exact: true })).toBeEnabled()
  }
  expect(state.deletes).toBe(5)
  state.turns = [{ ...answer('expired'), question: null, answer: null, message: null, citations: null, sources: null, body_available: false }]
  await page.reload(); await expectHydrated(page); await page.getByTestId('assistant-launcher').click()
  await expect(page.getByText('这条问答正文已到期清理。')).toBeVisible()
  let releaseDelete!: () => void
  state.hold = new Promise<void>(resolve => { releaseDelete = resolve })
  await page.getByRole('button', { name: '清除对话', exact: true }).click()
  await page.getByRole('button', { name: '确认清除' }).click()
  await expect.poll(() => state.deletes).toBe(6)
  await page.evaluate(() => {
    window.dispatchEvent(new PageTransitionEvent('pagehide'))
    window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true }))
  })
  releaseDelete(); state.hold = null
  await page.getByTestId('assistant-launcher').click()
  await expect(page.getByTestId('assistant-question')).toHaveCount(0)
  await expect(page.getByRole('button', { name: '重新开始' })).toBeEnabled()
  await page.getByRole('button', { name: '重新开始' }).click()
  await expect(page.getByLabel('问题', { exact: true })).toBeEnabled()
})


test('failed clear preserves visible history until server confirms deletion', async ({ page }) => {
  const state = await fixture(page, [answer('kept')])
  await expect(page.locator('.assistant-mode')).toHaveText('本地离线')
  state.deleteStatus = 503
  await page.getByRole('button', { name: '清除对话', exact: true }).click()
  await page.getByRole('button', { name: '确认清除', exact: true }).click()
  await expect(page.getByText('未能确认清除完成', { exact: true })).toBeVisible()
  await expect(page.getByTestId('assistant-question')).toContainText('隔离问题 kept')
  await expect(page.getByLabel('问题', { exact: true })).toBeDisabled()
  expect(state.posts).toBe(0)
  state.deleteStatus = 204
  await page.getByRole('button', { name: '清除对话', exact: true }).click()
  await page.getByRole('button', { name: '确认清除', exact: true }).click()
  await expect(page.getByText('本站可读问答已清除', { exact: true })).toBeVisible()
  await expect(page.getByTestId('assistant-question')).toHaveCount(0)
  await page.reload(); await expectHydrated(page)
  await page.getByTestId('assistant-launcher').click()
  await expect(page.getByTestId('assistant-question')).toHaveCount(0)
})

test('body-free feedback saves restores retracts and ignores a late result after clear', async ({ page }) => {
  const state = await fixture(page, [answer('feedback-turn')])
  const helpful = page.getByRole('button', { name: '有帮助', exact: true })
  const unhelpful = page.getByRole('button', { name: '没有帮助', exact: true })
  await page.getByRole('button', { name: '范围与数据说明', exact: true }).click()
  await expect(page.getByText('反馈仅保存赞或踩', { exact: false })).toBeVisible()
  await page.getByRole('button', { name: '范围与数据说明', exact: true }).click()
  await helpful.click()
  await expect(helpful).toHaveAttribute('aria-pressed', 'true')
  expect(state.feedbackCalls).toBe(1)
  await page.reload()
  await expectHydrated(page)
  await page.getByTestId('assistant-launcher').click()
  await expect(helpful).toHaveAttribute('aria-pressed', 'true')
  await helpful.click()
  await expect(helpful).toHaveAttribute('aria-pressed', 'false')
  state.feedbackFail = true
  await unhelpful.click()
  await expect(page.getByText('反馈未确认，请检查会话结果后再试。')).toBeVisible()
  await expect(unhelpful).toHaveAttribute('aria-pressed', 'false')
  state.feedbackFail = false
  let release!: () => void
  state.feedbackHold = new Promise<void>(resolve => { release = resolve })
  await helpful.click()
  await expect(helpful).toBeDisabled()
  await page.getByRole('button', { name: '清除对话', exact: true }).click()
  await page.getByRole('button', { name: '确认清除', exact: true }).click()
  await expect(page.locator('.assistant-turn')).toHaveCount(0)
  release()
  await expect(page.getByText('反馈已保存，可再次点击撤销。')).toHaveCount(0)
  expect(state.posts).toBe(0)
  expect(state.feedbackCalls).toBe(4)
})

test('feedback crosses the real proxy and appears in passive admin observations', async ({ page }) => {
  const feedbackPath = `/api/v1/assistant/turns/${'0'.repeat(32)}/feedback`
  expect((await page.request.get(feedbackPath)).status()).toBe(404)
  expect((await page.request.put(`${feedbackPath}?extra=1`, { data: { value: 'helpful' } })).status()).toBe(404)
  expect((await page.request.put('/api/v1/assistant/turns/invalid/feedback', { data: { value: 'helpful' } })).status()).toBe(404)
  await page.goto('/')
  await expectHydrated(page)
  await page.getByTestId('assistant-launcher').click()
  await submit(page, 'Which published notes cover FastAPI?')
  await expect(page.locator('.assistant-answer').first()).toBeVisible({ timeout: 30000 })
  await page.getByRole('button', { name: '有帮助', exact: true }).last().click()
  await expect(page.getByText('反馈已保存，可再次点击撤销。')).toBeVisible()
  await page.setViewportSize({ width: 390, height: 844 })
  expect((await new AxeBuilder({ page }).include('.assistant-feedback').withTags(['wcag2a', 'wcag2aa']).analyze()).violations).toEqual([])
  await page.goto('/admin/login')
  await expectHydrated(page)
  await page.getByTestId('username').fill('gavin')
  await page.getByTestId('password').fill('correct-horse')
  await page.getByTestId('login').click()
  await expect(page).toHaveURL(/\/admin\/articles$/)
  await page.goto('/admin/assistant')
  await expectHydrated(page)
  await expect(page.getByRole('heading', { name: '短会话反馈' })).toBeVisible()
  await expect(page.getByText('有帮助 1 · 没有帮助 0', { exact: true })).toBeVisible()
  await page.getByText('今日阶段耗时', { exact: true }).click()
  await expect(page.getByText('输出校验：', { exact: false })).toBeVisible()
  await page.route('**/api/v1/admin/assistant', async route => {
    const response = await route.fetch()
    const value = await response.json()
    value.daily_activity.errors = 2
    await route.fulfill({ response, json: value })
  })
  await page.getByRole('button', { name: '刷新状态' }).click()
  await expect(page.getByRole('heading', { name: '今日 2 次回答失败' })).toBeVisible()
})
