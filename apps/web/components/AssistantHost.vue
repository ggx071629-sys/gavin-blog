<template>
  <div v-if="visible" class="assistant-host">
    <AssistantDiscovery />
    <AssistantPanel
      v-if="loaded"
      :open="open"
      :mobile="mobile"
      :draft="draft"
      :policy="policy"
      :turns="turns"
      :stage="stage"
      :notice="notice"
      :busy="busy"
      :hydrating="hydrating"
      :live-enabled="liveEnabled"
      :has-unseen="hasUnseen"
      :confirm-clear="confirmClear"
      :examples="examples"
      :local-dev="localDev"
      :pending-question="pendingQuestion"
      :input-blocked="inputBlocked"
      :clearing="clearing"
      :feedback-pending="feedbackPending"
      :feedback-status="feedbackStatus"
      @feedback="submitFeedback"
      @close="closeFromUi"
      @closed="restoreEntryFocus"
      @update:draft="onDraft"
      @submit="submit"
      @example="fillExample"
      @clear="requestClear"
      @confirm-clear="confirmDelete"
      @cancel-clear="confirmClear = false"
      @resync="resync"
      @restart="restart"
      @refresh="refreshStatus"
      @source="onSource"
      @seen="hasUnseen = false"
    />
  </div>
</template>

<script setup lang="ts">
import '~/assets/css/assistant.css'
import type { AssistantClientPolicy, AssistantSessionTurn } from '~/types/api'
import { isAssistantLauncherPath } from '~/utils/assistant/allowlist'
import { sameOriginApiBase } from '~/utils/assistant/origin'
import { COUNT_POINTS, emptyAssistantMemory } from '~/utils/assistant/persistence'
import { mapAssistantCode, parseRetryAfter, type AssistantNotice } from '~/utils/assistant/errors'
import { AssistantSseError, AssistantSseParser } from '~/utils/assistant/sse'
import { closeAnswerCitations } from '~/utils/assistant/citations'
import { AssistantGenerationFence } from '~/utils/assistant/generation'
import {
  ASSISTANT_POLL_INTERVAL_MS,
  nextPollingDelay,
  pollingHorizonExpired,
} from '~/utils/assistant/polling'
import {
  AssistantHttpError,
  bootstrapSession,
  deleteSession,
  loadSession,
  saveFeedback,
  streamQuestion,
} from '~/utils/assistant/client'

const PanelLoader = () => import('~/components/AssistantPanel.vue')
const AssistantPanel = defineAsyncComponent(PanelLoader)

const route = useRoute()
const config = useRuntimeConfig()
const overlay = usePublicOverlay()
const localDev = config.public.assistantLocalDevMode === true
const entry = useAssistantEntry()
const visible = entry.visible
const open = entry.open
let returnSource: 'header' | 'orb' = 'header'
const loaded = ref(false)
const mobile = ref(false)
const draft = ref('')
const pendingQuestion = ref('')
const clearing = ref(false)
const feedbackPending = ref<string | null>(null)
const feedbackStatus = ref('')
const resetRequired = ref(false)
const awaitingResult = ref(false)
const unavailable = ref(false)
let pendingTurnId: string | null = null
const policy = ref<AssistantClientPolicy | null>(null)
const turns = ref<AssistantSessionTurn[]>([])
const stage = ref<string | null>(null)
const notice = ref<AssistantNotice | null>(null)
const busy = ref(false)
const hydrating = ref(false)
const liveEnabled = ref(false)
const hasUnseen = ref(false)
const confirmClear = ref(false)
const bootstrapped = ref(false)
const inputBlocked = computed(() => clearing.value || resetRequired.value || awaitingResult.value || unavailable.value || !bootstrapped.value || !policy.value)
const generation = new AssistantGenerationFence()
const inFlight = ref(false)
const memory = emptyAssistantMemory()
let pollTimer: number | null = null
let pollStartedAt: number | null = null
let focusMainAfterRoute = false
const examples = [
  '本站最近写了哪些技术文章？',
  '有哪些已发布的项目？',
]

const originOk = () => {
  if (!import.meta.client) return false
  return sameOriginApiBase(String(config.public.apiBase), window.location.origin)
}

const mediaMobile = () => window.matchMedia('(max-width: 1279px)').matches

const controller = () => {
  return generation.controller()
}

const releaseController = (item: AbortController) => generation.release(item)

const clearRawMemory = () => {
  feedbackPending.value = null
  feedbackStatus.value = ''
  Object.assign(memory, emptyAssistantMemory())
  draft.value = ''
  pendingQuestion.value = ''
  pendingTurnId = null
  awaitingResult.value = false
  unavailable.value = false
  hydrating.value = false
  turns.value = []
  stage.value = null
  policy.value = null
  hasUnseen.value = false
  busy.value = false
  inFlight.value = false
}

watch(entry.request, async (request) => {
  if (!visible.value) return
  if (open.value && request.source === 'header') closeFromUi()
  else {
    returnSource = request.source
    await openPanel()
  }
})

const openPanel = async () => {
  if (!originOk()) {
    notice.value = mapAssistantCode('origin_rejected')
    return
  }
  mobile.value = mediaMobile()
  overlay.claim('assistant', { restoreFocus: false })
  loaded.value = true
  open.value = true
  if (!bootstrapped.value && !clearing.value && !hydrating.value && !resetRequired.value) {
    const current = generation.value
    const request = controller()
    hydrating.value = true
    liveEnabled.value = false
    try {
      const created = await bootstrapSession(window.location.origin, String(config.public.apiBase), request.signal)
      if (current !== generation.value) return
      policy.value = created.policy
      const view = await loadSession(window.location.origin, String(config.public.apiBase), request.signal)
      if (current !== generation.value) return
      turns.value = view.turns
      policy.value = view.policy
      unavailable.value = false
      if (view.active_turn) {
        pendingQuestion.value = view.active_turn.question || ''
        pendingTurnId = view.active_turn.turn_id
        stage.value = view.active_turn.stage
        startPolling(current)
      }
      else {
        notice.value = view.turns.length ? { kind: 'info', title: `已恢复 ${view.turns.length} 轮`, body: '可以继续阅读或追问本站内容。' } : null
      }
      bootstrapped.value = true
    }
    catch (error) {
      if (current === generation.value) handleError(error, { afterQuestion: false })
    }
    finally {
      releaseController(request)
      if (current === generation.value) {
        hydrating.value = false
        liveEnabled.value = true
      }
    }
  }
}

const closeFromUi = () => {
  open.value = false
  overlay.release('assistant', { restoreFocus: true })
}

const restoreEntryFocus = () => {
  if (open.value || overlay.owner.value || !overlay.restoreFocus.value) return
  const trigger = document.querySelector<HTMLButtonElement>(`[data-assistant-entry="${returnSource}"]`)
    ?? document.querySelector<HTMLButtonElement>('[data-assistant-entry="header"]')
  trigger?.focus()
}

const hideOnly = () => {
  open.value = false
  overlay.release('assistant', { restoreFocus: false })
}

const onDraft = (value: string) => {
  const max = policy.value?.question_max_chars ?? 500
  if (COUNT_POINTS(value) <= Math.min(max, 2000)) draft.value = value
}

const fillExample = (value: string) => {
  draft.value = value
}

const submit = async () => {
  if (inFlight.value || busy.value || hydrating.value || inputBlocked.value || confirmClear.value) return
  const max = policy.value?.question_max_chars ?? 500
  const text = draft.value.trim()
  if (!text || COUNT_POINTS(text) > max) return
  if (!originOk()) {
    notice.value = mapAssistantCode('origin_rejected')
    return
  }
  inFlight.value = true
  busy.value = true
  notice.value = null
  stage.value = 'checking'
  const key = crypto.randomUUID()
  const payload = { question: text, current_path: route.path }
  memory.idempotencyKey = key
  memory.payload = payload
  memory.lastEventId = 0
  pendingTurnId = null
  pendingQuestion.value = text
  draft.value = ''
  await runStream(key, payload, 0, 0, new AssistantSseParser())
}

const runStream = async (
  key: string,
  payload: { question: string, current_path: string },
  lastId: number,
  attempt: number,
  parser: AssistantSseParser,
) => {
  const current = generation.value
  const request = controller()
  try {
    for await (const event of streamQuestion(
      window.location.origin,
      String(config.public.apiBase),
      payload,
      key,
      lastId || null,
      parser,
      request.signal,
    )) {
      if (current !== generation.value) return
      memory.lastEventId = event.event_id
      pendingTurnId = event.turn_id
      if (event.event === 'answer' || event.event === 'refusal' || event.event === 'error') {
        if (event.event === 'answer') {
          const closed = closeAnswerCitations(String(event.answer || ''), event.citations, event.sources)
          if (!closed) {
            notice.value = { kind: 'alert', title: '回答无法显示', body: '来源无法校验，已隐藏这份答案。' }
          }
          else {
            turns.value = [...turns.value, {
              turn_id: event.turn_id,
              created_at: new Date().toISOString(),
              status: 'answer',
              code: event.code,
              message: event.message,
              question: payload.question,
              answer: String(event.answer),
              citations: closed.markers.map(marker => marker.citation),
              sources: closed.sources,
              body_available: true,
            }]
            pendingQuestion.value = ''
          }
        }
        else {
          if (event.event === 'error') {
            handleError(new AssistantHttpError(200, event.code, null), { afterQuestion: true })
          }
          else {
            turns.value = [...turns.value, {
              turn_id: event.turn_id, created_at: new Date().toISOString(),
              status: event.event, code: event.code, message: null,
              question: payload.question, answer: null, citations: null, sources: null, body_available: true,
            }]
            pendingQuestion.value = ''
          }
        }
        stage.value = null
        busy.value = false
        inFlight.value = false
        pollStartedAt = null
        hasUnseen.value = true
        return
      }
      if (event.event === 'checking' || event.event === 'retrieving' || event.event === 'composing' || event.event === 'validating') {
        stage.value = event.stage
      }
    }
    if (current === generation.value) {
      startPolling(current)
      inFlight.value = false
    }
  }
  catch (error) {
    if (current !== generation.value) return
    const transportFailure = !(error instanceof AssistantSseError) && !(error instanceof AssistantHttpError)
    if (transportFailure && attempt < 2 && memory.idempotencyKey === key && memory.payload === payload) {
      await new Promise(resolve => setTimeout(resolve, 400 * (attempt + 1)))
      if (current !== generation.value) return
      await runStream(key, payload, memory.lastEventId || 0, attempt + 1, parser)
      return
    }
    handleError(error, { afterQuestion: true })
    if (transportFailure) startPolling(current)
    inFlight.value = false
  }
  finally {
    releaseController(request)
  }
}

const startPolling = (current = generation.value) => {
  stopPolling()
  if (pollStartedAt === null) pollStartedAt = Date.now()
  busy.value = true
  awaitingResult.value = true
  notice.value = { kind: 'info', title: '正在完成上一个问题', body: '刷新后只读取已有结果，不会用新的问题再问一次。' }
  schedulePoll(current, ASSISTANT_POLL_INTERVAL_MS)
}

const schedulePoll = (current: number, delayMs: number) => {
  if (current !== generation.value) return
  if (pollStartedAt !== null && pollingHorizonExpired(pollStartedAt, Date.now())) {
    stopPolling()
    notice.value = { kind: 'info', title: '自动等待已结束', body: '可手动检查结果；确认上次结果前暂不能继续提问。', action: 'refresh' }
    busy.value = false
    return
  }
  pollTimer = window.setTimeout(() => void pollStatus(current), delayMs)
}

const stopPolling = () => {
  if (pollTimer) {
    window.clearTimeout(pollTimer)
    pollTimer = null
  }
}

const pollStatus = async (current: number) => {
  if (current !== generation.value) return
  const request = controller()
  try {
    const view = await loadSession(window.location.origin, String(config.public.apiBase), request.signal)
    if (current !== generation.value) return
    const changed = JSON.stringify(turns.value) !== JSON.stringify(view.turns)
    turns.value = view.turns
    policy.value = view.policy
    bootstrapped.value = true
    unavailable.value = false
    if (changed) hasUnseen.value = true
    if (pendingTurnId && view.turns.some(turn => turn.turn_id === pendingTurnId)) pendingQuestion.value = ''
    if (!view.active_turn) {
      stopPolling()
      pollStartedAt = null
      stage.value = null
      busy.value = false
      awaitingResult.value = false
      pendingQuestion.value = ''
      notice.value = null
    }
    else {
      pendingTurnId = view.active_turn.turn_id
      pendingQuestion.value = view.active_turn.question || pendingQuestion.value
      awaitingResult.value = true
      busy.value = true
      stage.value = view.active_turn.stage
      schedulePoll(current, nextPollingDelay(200, true, null)!)
    }
  }
  catch (error) {
    if (current !== generation.value) return
    if (error instanceof AssistantHttpError && [429, 503].includes(error.status)) {
      const seconds = parseRetryAfter(error.retryAfter)
      const delay = nextPollingDelay(error.status, true, error.retryAfter)
      if (seconds && delay) {
        notice.value = { ...mapAssistantCode(error.code), body: `将在 ${seconds} 秒后继续检查。` }
        schedulePoll(current, delay)
      }
      else {
        stopPolling()
        busy.value = false
        notice.value = { ...mapAssistantCode(error.code), action: 'refresh' }
      }
      return
    }
    stopPolling()
    handleError(error, { afterQuestion: true })
    if (!notice.value?.action && !unavailable.value) notice.value = { ...notice.value!, action: 'refresh' }
  }
  finally {
    releaseController(request)
  }
}

const submitFeedback = async (turnId: string, choice: 'helpful' | 'unhelpful') => {
  if (feedbackPending.value || clearing.value || hydrating.value || busy.value) return
  const turn = turns.value.find(item => item.turn_id === turnId && item.body_available && item.status === 'answer')
  if (!turn) return
  const value = turn.feedback === choice ? null : choice
  const current = generation.value
  const request = controller()
  const timeout = window.setTimeout(() => request.abort(), 10000)
  feedbackPending.value = turnId
  feedbackStatus.value = '正在保存反馈…'
  try {
    await saveFeedback(window.location.origin, String(config.public.apiBase), turnId, value, request.signal)
    if (current !== generation.value || clearing.value) return
    const view = await loadSession(window.location.origin, String(config.public.apiBase), request.signal)
    if (current !== generation.value || clearing.value) return
    const live = view.turns.find(item => item.turn_id === turnId)
    const index = turns.value.findIndex(item => item.turn_id === turnId)
    if (!live || index < 0) return
    turns.value[index] = live
    feedbackStatus.value = !live.body_available ? '回答已到期，反馈已删除。' : live.feedback ? '反馈已保存，可再次点击撤销。' : '反馈已撤销。'
  }
  catch {
    if (current === generation.value && !clearing.value) feedbackStatus.value = '反馈未确认，请检查会话结果后再试。'
  }
  finally {
    window.clearTimeout(timeout)
    releaseController(request)
    if (current === generation.value) feedbackPending.value = null
  }
}

const refreshStatus = async () => {
  if (clearing.value || hydrating.value || inFlight.value) return
  stopPolling()
  feedbackStatus.value = ''
  busy.value = true
  pollStartedAt = Date.now()
  await pollStatus(generation.value)
}

const handleError = (error: unknown, { afterQuestion }: { afterQuestion: boolean }) => {
  busy.value = false
  stage.value = null
  if (error instanceof AssistantHttpError) {
    unavailable.value = ['origin_rejected', 'assistant_disabled', 'assistant_not_ready', 'budget_exhausted', 'assistant_session_missing', 'assistant_session_expired', 'csrf_failed', 'session_revoking'].includes(error.code)
    if (error.code === 'provider_result_unknown') awaitingResult.value = true
    if (error.code === 'origin_rejected') {
      notice.value = mapAssistantCode(error.code)
      return
    }
    if (error.status === 401 && afterQuestion) {
      notice.value = mapAssistantCode(error.code)
      return
    }
    if (['rate_limited', 'concurrency_limited', 'stream_connection_limited'].includes(error.code)) {
      const seconds = parseRetryAfter(error.retryAfter)
      notice.value = seconds
        ? { ...mapAssistantCode(error.code), body: `请在 ${seconds} 秒后修改问题并显式发送；检查结果只读取已有回答。`, action: 'refresh' }
        : { ...mapAssistantCode(error.code), action: 'retry' }
      return
    }
    notice.value = mapAssistantCode(error.code)
    return
  }
  awaitingResult.value = afterQuestion
  notice.value = { kind: 'alert', title: '暂时无法确认上次回答是否完成', body: '连接中断。检查结果只读取已有回答，不会重新提问。', action: afterQuestion ? 'refresh' : 'restart' }
}

const requestClear = () => {
  if (!clearing.value) confirmClear.value = true
}
const confirmDelete = async () => {
  if (clearing.value) return
  clearing.value = true
  resetRequired.value = true
  confirmClear.value = false
  const current = generation.advance()
  stopPolling()
  pollStartedAt = null
  notice.value = mapAssistantCode('session_revoking')
  const request = controller()
  try {
    const result = await deleteSession(window.location.origin, String(config.public.apiBase), request.signal)
    if (current !== generation.value) return
    clearRawMemory()
    bootstrapped.value = false
    confirmClear.value = false
    if (result.status === 204) {
      resetRequired.value = false
      notice.value = {
        kind: 'info',
        title: '本站可读问答已清除',
        action: 'restart',
        body: localDev
          ? '本站可读问答正文与引用已清除；本地离线开发回答器未向云端模型发送内容。'
          : '本站可读问答正文与引用已清除。不含正文的最小费用记录最多再保留 48 小时。清除不能撤回已发送给模型供应商的数据。',
      }
    }
    else {
      notice.value = { ...mapAssistantCode('session_revoking'), action: 'restart' }
    }
  }
  catch {
    if (current !== generation.value) return
    confirmClear.value = false
    notice.value = {
      kind: 'alert',
      title: '未能确认清除完成',
      action: 'restart',
      body: '当前记录仍保留在页面中，服务端清理状态未知。可再次清除，或重新开始以核对会话；不会自动重新提交旧问题。',
    }
  }
  finally {
    releaseController(request)
    if (current === generation.value) clearing.value = false
  }
}

const resync = async () => {
  if (clearing.value || hydrating.value) return
  const current = generation.value
  const request = controller()
  hydrating.value = true
  try {
    const created = await bootstrapSession(window.location.origin, String(config.public.apiBase), request.signal)
    if (current !== generation.value) return
    policy.value = created.policy
    unavailable.value = false
    await pollStatus(current)
    if (current === generation.value && !unavailable.value && !awaitingResult.value) notice.value = { kind: 'info', title: '已重新同步', body: '不会自动重交上一个问题。' }
  }
  catch (error) {
    if (current === generation.value) handleError(error, { afterQuestion: false })
  }
  finally {
    releaseController(request)
    if (current === generation.value) hydrating.value = false
  }
}

const restart = async () => {
  if (clearing.value || hydrating.value) return
  if (resetRequired.value) {
    await confirmDelete()
    if (resetRequired.value) return
  }
  generation.advance()
  stopPolling()
  pollStartedAt = null
  clearRawMemory()
  bootstrapped.value = false
  await openPanel()
}

const onSource = (path: string) => {
  hideOnly()
  if (path === route.path) nextTick(focusMain)
  else focusMainAfterRoute = true
}
const focusMain = () => {
  const target = document.querySelector<HTMLElement>('#main-content, main, h1')
  if (target) {
    if (!target.hasAttribute('tabindex')) target.setAttribute('tabindex', '-1')
    target.focus()
  }
}

watch(() => overlay.owner.value, (owner) => {
  if (owner === 'nav' && open.value) open.value = false
})
watch(() => route.path, (path) => {
  if (!isAssistantLauncherPath(path)) {
    generation.advance()
    stopPolling()
    pollStartedAt = null
    clearRawMemory()
    clearing.value = false
    open.value = false
    loaded.value = false
    bootstrapped.value = false
  }
  else if (open.value) hideOnly()
  if (focusMainAfterRoute) {
    focusMainAfterRoute = false
    nextTick(() => {
      const target = document.querySelector<HTMLElement>('#main-content, main, h1')
      if (target) {
        if (!target.hasAttribute('tabindex')) target.setAttribute('tabindex', '-1')
        target.focus()
      }
    })
  }
})
const onResize = () => {
  mobile.value = mediaMobile()
}
const onPageHide = () => {
  generation.advance()
  stopPolling()
  pollStartedAt = null
  clearRawMemory()
  clearing.value = false
  confirmClear.value = false
  bootstrapped.value = false
  notice.value = resetRequired.value
    ? { kind: 'info', title: '本地视图已清除', body: '服务端清理尚未确认。重新开始前会再次确认清除。', action: 'restart' }
    : null
  hideOnly()
}
const onPageShow = (event: PageTransitionEvent) => {
  if (event.persisted) onPageHide()
}
onMounted(() => {
  window.addEventListener('resize', onResize)
  window.addEventListener('pagehide', onPageHide)
  window.addEventListener('pageshow', onPageShow)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('pagehide', onPageHide)
  window.removeEventListener('pageshow', onPageShow)
  open.value = false
  generation.advance()
  stopPolling()
  overlay.release('assistant', { restoreFocus: false })
})
</script>
