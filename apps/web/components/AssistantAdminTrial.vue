<template>
  <section class="am-trial" aria-labelledby="trial-heading">
    <div class="am-trial-intro">
      <h2 id="trial-heading">试问你的助手</h2>
      <p>以访客的视角，检查回答是否清楚、引用是否准确。</p>
      <p class="am-hint">仅管理员可见 · 使用当前公开知识 · 计入今日预算</p>
      <p v-if="publicClosed" class="am-hint">试问不会向访客开放助手。</p>
      <button class="am-link" :disabled="clearing || !hasSession" @click="clear">{{ clearing ? '清空中…' : '清空试问' }}</button>
    </div>
    <div class="am-trial-chat">
    <p v-if="!available" class="am-alert">当前试问条件尚未满足，请到高级维护查看诊断或恢复已停止的试问。</p>
    <p v-if="notice" role="status" class="am-hint">{{ notice }}</p>
    <p v-if="error" role="alert" class="am-alert">{{ error }}</p>
    <div v-if="!turns.length" class="am-trial-empty"><StudioIcon name="message-circle" /><h3>从一个具体问题开始</h3><p>检查回答是否准确，再展开依据查看公开来源。</p>
      <button class="am-example" @click="draft = 'Gavin 写过哪些关于 FastAPI 的文章？'">Gavin 写过哪些关于 FastAPI 的文章？</button>
    </div>
    <article v-for="turn in turns" :key="turn.turn_id" class="am-turn">
      <p class="am-question">{{ turn.question || '问答正文已过期' }}</p>
      <p class="am-answer">{{ turn.answer ? displayLiteral(turn.answer) : turn.message || '未找到足够依据' }}</p>
      <details v-if="turn.evidence.length"><summary>查看回答依据（{{ turn.evidence.length }} 处）</summary>
        <div v-for="source in turn.evidence" :key="source.n" class="am-source">
          <strong>[{{ source.n }}] {{ source.title }}</strong><blockquote>{{ source.excerpt }}</blockquote>
          <a :href="source.path" :download="isResumeSourcePath(source.path) || undefined" target="_blank" rel="noopener">{{ isResumeSourcePath(source.path) ? '下载简历 PDF' : '查看原文' }} <span class="sr-only">{{ source.title }}{{ isResumeSourcePath(source.path) ? '（文件下载）' : '（新窗口）' }}</span>↗</a>
        </div>
      </details>
      <small>本次费用 {{ turn.cost_micro_cny === null ? '待结算' : money(turn.cost_micro_cny) }}</small>
    </article>
    <p v-if="busy" role="status">{{ stage || '正在处理问题…' }}</p>
    <button v-if="pending" class="am-link" :disabled="busy" @click="restore">刷新回答结果</button>
    <form class="am-composer" @submit.prevent="submit">
      <label for="trial-question">你的问题</label>
      <textarea id="trial-question" v-model="draft" rows="3" maxlength="2000" placeholder="针对本站公开内容提问…" :disabled="busy || clearing" @keydown.ctrl.enter.prevent="submit" @keydown.meta.enter.prevent="submit" />
      <div><small>Ctrl / ⌘ + Enter 发送 · 回答和依据仅短期保留</small>
        <button v-if="busy" type="button" class="button-secondary" @click="stop">停止接收</button>
        <button v-else type="submit" class="button-primary" :disabled="!available || !draft.trim() || pending || clearing"><StudioIcon name="send" />发送问题</button>
      </div>
    </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { displayLiteral } from '~/utils/assistant/citations'
import { AssistantSseParser } from '~/utils/assistant/sse'
import { isResumeSourcePath } from '~/utils/assistant/allowlist'
import { assistantRequest } from '~/utils/assistant/client'
import { money, trialCitations, type TrialCitation } from '~/utils/assistant-management'
import { mapAssistantCode } from '~/utils/assistant/errors'

const props = defineProps<{ available: boolean, publicClosed: boolean }>()
const emit = defineEmits<{ settled: [] }>()
type Turn = { turn_id: string, question: string | null, answer: string | null, message: string | null, cost_micro_cny: number | null, evidence: TrialCitation[] }
const config = useRuntimeConfig()
const adminCsrf = useCookie<string>('gavin_csrf')
const draft = ref('')
const turns = ref<Turn[]>([])
const hasSession = ref(false)
const busy = ref(false)
const clearing = ref(false)
const pending = ref(false)
const stage = ref('')
const error = ref('')
const notice = ref('')
let csrf = ''
let revision = 0
let controller: AbortController | null = null
const readCsrf = () => decodeURIComponent(document.cookie.match(/(?:^|; )gavin_trial_csrf=([^;]*)/)?.[1] || '')
const restore = async () => {
  const current = revision
  try {
    const result = await apiFetch<{ turns: (Omit<Turn, 'evidence'> & { citations: unknown, sources: unknown })[], active_turn: unknown }>('/admin/assistant/trial/session')
    if (current !== revision) return
    turns.value = result.turns.map(turn => ({ ...turn, evidence: turn.answer ? trialCitations(turn.answer, turn.citations, turn.sources) : [] }))
    hasSession.value = true
    pending.value = !!result.active_turn
    csrf = readCsrf()
    error.value = ''
    if (!pending.value) notice.value = ''
  }
  catch (cause) {
    if (current !== revision) return
    const status = (cause as { statusCode?: number }).statusCode
    if (status === 401) { hasSession.value = false; pending.value = false }
    else error.value = '暂时无法恢复回答，请刷新结果。'
  }
}
const submit = async () => {
  if (!props.available || busy.value || pending.value || clearing.value || !draft.value.trim()) return
  busy.value = true; error.value = ''; notice.value = ''
  const current = ++revision
  controller = new AbortController()
  const question = draft.value.trim()
  try {
    const session = await apiFetch<{ csrf_token: string }>('/admin/assistant/trial/sessions', { method: 'POST', signal: controller.signal })
    if (current !== revision) return
    csrf = session.csrf_token; hasSession.value = true
    pending.value = true
    const response = await assistantRequest('/admin/assistant/trial/questions', {
      method: 'POST', signal: controller.signal, headers: {
        'Content-Type': 'application/json', 'X-CSRF-Token': adminCsrf.value || '',
        'X-Assistant-CSRF': csrf, 'Idempotency-Key': `trial-${crypto.randomUUID()}`,
      }, body: JSON.stringify({ question }),
    }, window.location.origin, String(config.public.apiBase))
    if (!response.ok) {
      pending.value = false
      const payload = await response.json()
      const message = mapAssistantCode(payload?.error?.code || '')
      throw new Error(`${message.title}：${message.body}`)
    }
    if (!response.body || !response.headers.get('content-type')?.startsWith('text/event-stream')) throw new Error('未收到有效回答流')
    pending.value = true
    const reader = response.body.getReader()
    const parser = new AssistantSseParser()
    while (true) {
      const result = await reader.read()
      if (current !== revision) { await reader.cancel(); return }
      if (result.done) { parser.finish(); break }
      for (const event of parser.push(result.value)) {
        if ('stage' in event) stage.value = ({ checking: '检查问题…', retrieving: '检索公开内容…', composing: '生成回答…', validating: '核对回答依据…' })[event.stage]
        else {
          turns.value.push({ turn_id: event.turn_id, question, answer: event.answer || null,
            message: event.event === 'answer' ? null : mapAssistantCode(event.code).body,
            cost_micro_cny: null, evidence: event.answer ? trialCitations(event.answer, event.citations, event.sources) : [] })
          pending.value = false; draft.value = ''
        }
      }
    }
    await restore()
    emit('settled')
  }
  catch (cause) {
    if (current === revision && !(cause instanceof Error && cause.name === 'AbortError')) error.value = '试问未确认完成，服务可能正在维护。请刷新回答结果并核对运行状态，避免重复计费。'
  }
  finally { if (current === revision) { busy.value = false; stage.value = ''; controller = null } }
}
const stop = () => { controller?.abort(); notice.value = '已停止接收，后台调用可能仍在处理和计费。请刷新回答结果。' }
const clear = async () => {
  if (clearing.value) return
  clearing.value = true; revision++; controller?.abort(); busy.value = false
  try {
    const result = await apiFetch<{ error?: { code: string } } | null>('/admin/assistant/trial/session', { method: 'DELETE', headers: { 'X-Assistant-CSRF': csrf || readCsrf() } })
    turns.value = []; hasSession.value = false; pending.value = false; csrf = ''; draft.value = ''
    notice.value = result?.error?.code === 'session_revoking' ? '试问已撤销，后台仍在清理；已发送调用可能继续结算。' : '已清空试问；已发送的调用仍可能结算费用。'; error.value = ''
    emit('settled')
  }
  catch { error.value = '清空未确认完成，请重试。'; pending.value = true }
  finally { clearing.value = false }
}
onMounted(restore)
onBeforeUnmount(() => { revision++; controller?.abort() })
</script>
