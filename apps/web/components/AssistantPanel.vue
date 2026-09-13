<template>
  <Teleport to="body">
    <Transition name="assistant"><div v-if="open" class="assistant-shell" :style="viewportStyle" :class="{ 'assistant-shell-mobile': mobile, 'assistant-shell-desktop': !mobile }" :data-testid="mobile ? 'assistant-modal' : 'assistant-panel'" @click.self="mobile && $emit('close')">
      <section id="ask-gavin-panel" ref="dialogEl" tabindex="-1" class="assistant-dialog" role="dialog" :aria-modal="mobile ? 'true' : undefined" aria-labelledby="ask-gavin-title" @keydown="onKeydown">
        <header class="assistant-dialog-header">
          <div class="assistant-identity">
            <span class="assistant-mark" aria-hidden="true">G</span>
            <div class="assistant-heading"><h2 id="ask-gavin-title" class="assistant-title">问 Gavin</h2><p class="assistant-subtitle">AI 助手 · 仅依据本站已收录的公开内容</p></div>
          </div>
          <span v-if="localDev" class="assistant-mode">本地离线</span>
          <button class="icon-button assistant-close" type="button" aria-label="关闭问答面板" @click="$emit('close')"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg></button>
        </header>
        <div class="assistant-log-wrap">
          <div ref="logEl" tabindex="0" class="assistant-log" role="log" aria-label="问答记录" :aria-live="liveEnabled ? 'polite' : 'off'" @scroll="onScroll">
            <div v-if="!hasConversation && !hydrating" class="assistant-welcome">
              <div data-focus-card class="assistant-welcome-card">
              <p class="assistant-kicker">从本站内容开始</p>
              <h3 class="assistant-welcome-heading">读到这里，<br>还有什么想了解？</h3>
              <p class="assistant-welcome-copy">我会从已收录的公开内容中寻找依据，<br class="assistant-welcome-break">并附上可以继续阅读的原文。</p>
              </div>
              <ul class="assistant-examples">
                <li v-for="item in examples.slice(0, 2)" :key="item"><button type="button" data-focus-card class="assistant-example" :disabled="busy || hydrating || inputBlocked" @click="chooseExample(item)"><span>{{ item }}</span><svg class="assistant-example-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M5 12h14m-5-5 5 5-5 5"/></svg></button></li>
              </ul>
            </div>
            <article v-for="turn in turns" :key="turn.turn_id" class="assistant-turn" tabindex="-1" :data-turn-id="turn.turn_id">
              <div v-if="turn.question" class="assistant-question-wrap"><p class="assistant-message-label">你</p><p class="assistant-question" data-testid="assistant-question">{{ turn.question }}</p></div>
              <p v-if="!turn.body_available" class="assistant-tombstone">这条问答正文已到期清理。</p>
              <div v-else-if="turn.status !== 'answer'" data-focus-card class="assistant-notice"><div class="assistant-notice-copy"><strong>{{ mapAssistantCode(turn.code || '').title }}</strong><p>{{ mapAssistantCode(turn.code || '').body }}</p><NuxtLink v-if="turn.code === 'insufficient_evidence'" to="/search" class="assistant-text-action" @click="$emit('source', '/search')">搜索本站</NuxtLink></div></div>
              <template v-else>
                <div class="assistant-answer-label"><span aria-hidden="true"/>Gavin <span class="assistant-ai-label">AI</span></div>
                <div class="assistant-answer-body">
                  <p v-for="(paragraph, index) in paragraphs(turn.answer)" :key="index" class="assistant-answer" data-testid="assistant-answer"><template v-for="(part, partIndex) in splitAnswerMarkers(paragraph)" :key="partIndex"><button v-if="part.marker" class="assistant-citation" type="button" :aria-label="'查看来源 ' + part.marker" @click="jumpToSource(turn.turn_id, part.marker, $event)">[{{ part.marker }}]</button><span v-else>{{ part.text }}</span></template></p>
                </div>
                <p v-if="turn.sources?.length" class="assistant-sources-title">参考来源 <span>· {{ turn.sources.length }}</span></p>
                <ol v-if="turn.sources?.length" class="assistant-sources" aria-label="本回答的参考来源">
                  <li v-for="source in turn.citations" :id="sourceId(turn.turn_id, source.n)" :key="source.n + '-' + source.path" tabindex="-1" data-focus-card class="assistant-source-row" :class="{ 'is-selected': selectedSource === sourceId(turn.turn_id, source.n) }">
                    <span class="assistant-source-n">{{ source.n }}</span>
                    <a v-if="isResumeSourcePath(source.path)" :href="source.path" class="assistant-source-main assistant-source-link" download><span class="assistant-source-copy"><span class="assistant-source-path">PDF · 回答所据版本</span><span>{{ source.title }}</span></span><span aria-hidden="true">↓</span></a>
                    <NuxtLink v-else :to="source.path" class="assistant-source-main assistant-source-link" @click="$emit('source', source.path)"><span class="assistant-source-copy"><span>{{ source.title }}</span></span><svg class="assistant-source-arrow" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M7 17 17 7M7 7h10v10"/></svg></NuxtLink>
                    <p class="assistant-source-location">{{ source.heading_path || '未提供章节定位，请在来源正文中核查。' }}</p>
                    <button v-if="selectedSource === sourceId(turn.turn_id, source.n)" type="button" class="assistant-return-citation" @click="returnToCitation">返回引用</button>
                  </li>
                </ol>
                <div class="assistant-feedback" role="group" aria-label="回答反馈">
                  <button type="button" class="assistant-text-action" :aria-pressed="turn.feedback === 'helpful'" :disabled="!!feedbackPending || busy || hydrating || clearing" @click="$emit('feedback', turn.turn_id, 'helpful')">有帮助</button>
                  <button type="button" class="assistant-text-action" :aria-pressed="turn.feedback === 'unhelpful'" :disabled="!!feedbackPending || busy || hydrating || clearing" @click="$emit('feedback', turn.turn_id, 'unhelpful')">没有帮助</button>
                </div>
              </template>
            </article>
            <div v-if="pendingQuestion" class="assistant-pending">
              <div class="assistant-question-wrap"><p class="assistant-message-label">你</p><p class="assistant-question" data-testid="assistant-question">{{ pendingQuestion }}</p></div>
            </div>
            <p v-if="feedbackStatus" class="assistant-feedback-status" role="status">{{ feedbackStatus }} <button v-if="feedbackStatus.includes('未确认')" type="button" class="assistant-text-action" :disabled="busy || hydrating || clearing || !!feedbackPending" @click="$emit('refresh')">检查反馈</button></p>
            <div v-if="stage || hydrating" class="assistant-stage"><span class="assistant-stage-node" aria-hidden="true"/><span>{{ hydrating ? '正在恢复短会话…' : stageLabel }}</span></div>
            <div v-if="visibleNotice" :role="visibleNotice.kind === 'alert' ? 'alert' : undefined" data-focus-card class="assistant-notice" :class="{ 'is-alert': visibleNotice.kind === 'alert' }"><span class="assistant-notice-icon" aria-hidden="true">{{ visibleNotice.kind === 'alert' ? '!' : 'i' }}</span><div class="assistant-notice-copy"><strong>{{ visibleNotice.title }}</strong><p>{{ visibleNotice.body }}</p><button v-if="visibleNotice.action === 'resync'" type="button" class="assistant-text-action" :disabled="busy || hydrating || clearing" @click="$emit('resync')">重新同步</button><button v-if="visibleNotice.action === 'restart'" type="button" class="assistant-text-action" :disabled="busy || hydrating || clearing" @click="$emit('restart')">重新开始</button><button v-if="visibleNotice.action === 'refresh' || visibleNotice.action === 'retry'" type="button" class="assistant-text-action" :disabled="busy || hydrating || clearing" @click="$emit('refresh')">检查结果</button></div></div>
          </div>
          <button v-if="hasUnseen && !nearBottom" type="button" class="assistant-unseen" @click="showNewReply">查看新回复 <span aria-hidden="true">↓</span></button>
        </div>
        <form v-if="!confirmClear" class="assistant-composer" @submit.prevent="$emit('submit')">
          <div class="assistant-composer-tools"><button type="button" class="assistant-policy-toggle" :aria-expanded="policyOpen" aria-controls="assistant-data-policy" @click="policyOpen = !policyOpen"><svg viewBox="0 0 20 20" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><circle cx="10" cy="10" r="7"/><path d="M10 9v5m0-9v1"/></svg>范围与数据说明</button><button type="button" class="assistant-text-action assistant-clear-action" :disabled="clearing" @click="$emit('clear')">清除对话</button></div>
          <div v-if="policyOpen" id="assistant-data-policy" tabindex="0" class="assistant-data-copy" role="region" aria-label="范围与数据说明">
            <p>反馈仅保存赞或踩，不附带问答正文，用于了解回答是否有帮助。可再次点击撤销，随原回答到期或清除会话删除，不延长问答留存。</p>
            <template v-if="localDev"><p>当前为本地离线开发回答器，不是站长本人，也不代表云端模型回答质量。</p><p>问题只在本机处理，并从开发内容库的已发布内容中生成带引用的确定性摘录；不会发送给云端模型。</p></template>
            <template v-else><p>这是 AI，不是站长本人。只依据已收录的本站公开内容和站长导入的公开简历，不进行联网搜索。</p><p>本次问题、必要公开片段和已明确的来源名称会发送给云端模型。短会话最多保留 4 轮历史供对象核对，旧答案不作为新事实。不要粘贴 JD、联系方式、凭据或第三方机密。</p><p>清除本站短会话不能撤回已发送给模型供应商的数据，也不能改变供应商留存政策。</p></template>
            <p v-if="policy">{{ policyText }}</p>
          </div>
          <div class="assistant-input-wrap">
            <label class="sr-only" for="ask-gavin-input">问题</label>
            <textarea id="ask-gavin-input" ref="inputEl" :value="draft" class="assistant-input" rows="2" maxlength="2000" autocomplete="off" :placeholder="hasConversation ? '继续追问本站内容…' : '想了解本站的什么内容？'" :disabled="busy || hydrating || inputBlocked" @compositionstart="composing = true" @compositionend="composing = false" @input="onDraftInput" @keydown="onInputKey" />
            <div class="assistant-composer-meta"><span class="assistant-count">{{ count }}<span v-if="policy"> / {{ maxChars }}</span><span v-else> · 限制尚未取得</span></span><span v-if="busy || hydrating || inputBlocked" class="assistant-input-status">{{ clearing ? "正在清除" : hydrating ? "正在连接" : busy ? "请等待当前回答" : "请先处理会话提示" }}</span><button type="submit" class="assistant-send" :disabled="busy || hydrating || inputBlocked || !draft.trim() || count > maxChars">发送<svg class="assistant-send-arrow" viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M10 16V4m-5 5 5-5 5 5"/></svg></button></div>
          </div>
        </form>
        <div v-if="confirmClear" ref="confirmEl" data-focus-card class="assistant-confirm" role="group" aria-labelledby="ask-gavin-clear-title"><div class="assistant-confirm-copy"><strong id="ask-gavin-clear-title">清除本站短会话？</strong><p>{{ localDev ? '清除本站可读问答和引用。本地离线模式没有向云端发送内容。' : '清除本站可读问答和引用，不会停止模型，也不能撤回供应商已收到的数据。' }}</p></div><div class="assistant-confirm-actions"><button type="button" class="assistant-text-action" @click="$emit('cancel-clear')">取消</button><button type="button" class="assistant-send" @click="$emit('confirm-clear')">确认清除</button></div></div>
      </section>
    </div></Transition>
  </Teleport>
</template>

<script setup lang="ts">
import type { AssistantClientPolicy, AssistantSessionTurn } from '~/types/api'
import { COUNT_POINTS } from '~/utils/assistant/persistence'
import { mapAssistantCode, formatPolicyLimits, type AssistantNotice } from '~/utils/assistant/errors'
import { splitAnswerMarkers } from '~/utils/assistant/citations'
import { isResumeSourcePath } from '~/utils/assistant/allowlist'

const props = defineProps<{ open: boolean, mobile: boolean, draft: string, policy: AssistantClientPolicy | null, turns: AssistantSessionTurn[], stage: string | null, notice: AssistantNotice | null, busy: boolean, hydrating: boolean, liveEnabled: boolean, hasUnseen: boolean, confirmClear: boolean, examples: string[], localDev: boolean, pendingQuestion?: string, inputBlocked: boolean, clearing: boolean, feedbackPending?: string | null, feedbackStatus?: string }>()
const emit = defineEmits(['close', 'closed', 'update:draft', 'submit', 'example', 'clear', 'confirm-clear', 'cancel-clear', 'resync', 'restart', 'refresh', 'source', 'seen', 'feedback'])
const dialogEl = ref<HTMLElement | null>(null)
const inputEl = ref<HTMLTextAreaElement | null>(null)
const logEl = ref<HTMLElement | null>(null)
const confirmEl = ref<HTMLElement | null>(null)
const viewportStyle = ref<Record<string, string>>({})
const composing = ref(false)
const overlay = usePublicOverlay()
const policyOpen = ref(true)
const nearBottom = ref(true)
const selectedSource = ref('')
let citationTrigger: HTMLElement | null = null
const hasConversation = computed(() => props.turns.length > 0 || Boolean(props.pendingQuestion))
const maxChars = computed(() => Math.min(props.policy?.question_max_chars ?? 500, 2000))
const count = computed(() => COUNT_POINTS(props.draft))
const policyText = computed(() => props.policy ? formatPolicyLimits(props.policy) : '')
const stageLabel = computed(() => ({ checking: '正在核对问题…', retrieving: '正在检索公开内容…', composing: '正在组织回答…', validating: '正在校验引用…' }[props.stage || ''] || props.stage))
const visibleNotice = computed(() => props.notice)
const paragraphs = (answer: string | null) => (answer || '').split(/\n\n/)
const sourceId = (turn: string, n: number | string) => ['assistant-source', turn, n].join('-')
const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches
const jumpToSource = (turn: string, n: number | string, event: MouseEvent) => {
  const row = props.turns.find(item => item.turn_id === turn)
  const citation = row?.citations?.find(item => item.n === String(n))
  const source = row?.sources?.find(item => item.path === citation?.path && item.title === citation?.title)
  if (!source) return
  const id = sourceId(turn, n)
  citationTrigger = event.currentTarget as HTMLElement
  selectedSource.value = id
  nextTick(() => {
    const target = document.getElementById(id)
    target?.scrollIntoView({ block: 'nearest', behavior: reducedMotion() ? 'instant' : 'smooth' })
    target?.focus({ preventScroll: true })
  })
}
const returnToCitation = () => {
  citationTrigger?.scrollIntoView({ block: 'center', behavior: reducedMotion() ? 'instant' : 'smooth' })
  citationTrigger?.focus({ preventScroll: true })
  selectedSource.value = ''
}
const showNewReply = () => {
  const items = logEl.value?.querySelectorAll<HTMLElement>('.assistant-turn, .assistant-notice, .assistant-pending')
  const last = items?.[items.length - 1]
  if (last && logEl.value) {
    const answer = last.querySelector<HTMLElement>('.assistant-answer-label') || last
    const top = answer.getBoundingClientRect().top - logEl.value.getBoundingClientRect().top + logEl.value.scrollTop
    logEl.value.scrollTo({ top, behavior: reducedMotion() ? 'instant' : 'smooth' })
  }
  emit('seen')
}
const onScroll = () => {
  const node = logEl.value
  if (!node) return
  nearBottom.value = node.scrollHeight - node.scrollTop - node.clientHeight <= 48
  if (nearBottom.value) emit('seen')
}
const resizeInput = () => {
  const node = inputEl.value
  if (!node) return
  node.style.height = 'auto'
  node.style.height = Math.min(node.scrollHeight, 120) + 'px'
}
const onDraftInput = (event: Event) => {
  emit('update:draft', (event.target as HTMLTextAreaElement).value)
  nextTick(() => {
    if (inputEl.value) inputEl.value.value = props.draft
    resizeInput()
  })
}
const chooseExample = (question: string) => {
  emit('example', question)
  nextTick(() => { resizeInput(); inputEl.value?.focus() })
}
const background = () => [
  document.querySelector<HTMLElement>('.skip-link'),
  document.querySelector<HTMLElement>('.site-header'),
  document.querySelector<HTMLElement>('#main-content'),
  document.querySelector<HTMLElement>('footer'),
  document.querySelector<HTMLElement>('.assistant-launcher'),
  document.querySelector<HTMLElement>('.assistant-orb-layer'),
].filter((el): el is HTMLElement => Boolean(el))
const setInert = (locked: boolean) => {
  if (!locked && overlay.owner.value === 'nav') return
  for (const el of background()) el.inert = locked
  document.body.style.overflow = locked ? 'hidden' : ''
}
const focusable = () => Array.from((props.confirmClear ? confirmEl.value : dialogEl.value)?.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])') ?? []).filter(el => el.getClientRects().length > 0)
const onKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Escape') { event.preventDefault(); emit(props.confirmClear ? 'cancel-clear' : 'close'); return }
  if ((!props.mobile && !props.confirmClear) || event.key !== 'Tab') return
  const items = focusable()
  const first = items[0], last = items[items.length - 1]
  if (event.shiftKey && (document.activeElement === first || document.activeElement === dialogEl.value)) { event.preventDefault(); last?.focus() }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
}
const onInputKey = (event: KeyboardEvent) => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing && !composing.value && event.keyCode !== 229 && !window.matchMedia('(max-width: 639px)').matches) { event.preventDefault(); emit('submit') }
}
watch(() => props.draft, () => nextTick(resizeInput))
watch(hasConversation, (value) => { policyOpen.value = !value })
watch(() => props.pendingQuestion, async (value) => {
  if (!value || !nearBottom.value) return
  await nextTick()
  if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight
  nearBottom.value = true
})
watch(() => props.turns, async (turns, previous) => {
  const follow = nearBottom.value
  await nextTick()
  if (turns !== previous && follow && props.liveEnabled) showNewReply()
})
watch(visibleNotice, async (notice) => {
  if (!notice) return
  const follow = nearBottom.value
  await nextTick()
  if (follow) {
    logEl.value?.querySelector<HTMLElement>(':scope > .assistant-notice')?.scrollIntoView({ block: 'nearest', behavior: 'instant' })
    emit('seen')
  }
}, { immediate: true })
watch(() => props.open, async (open) => {
  await nextTick()
  if (open) {
    policyOpen.value = !hasConversation.value
    if (props.mobile) { overlay.claim('assistant', { restoreFocus: false }); setInert(true) }
    else setInert(false)
    const target = props.mobile ? dialogEl.value : inputEl.value
    target?.focus()
    resizeInput()
  }
  else {
    setInert(false)
    emit('closed')
  }
}, { immediate: true })
watch(() => props.mobile, (mobile) => {
  if (!props.open) return
  if (mobile) { overlay.claim('assistant', { restoreFocus: false }); setInert(true); dialogEl.value?.focus() }
  else setInert(false)
})
watch(() => overlay.owner.value, async (owner) => {
  if (!props.open || !props.mobile) return
  await nextTick()
  if (owner === 'assistant') { setInert(true); dialogEl.value?.focus() }
  else setInert(false)
})
const updateViewport = () => {
  const viewport = window.visualViewport
  viewportStyle.value = props.mobile && viewport
    ? { '--assistant-viewport-height': `${viewport.height}px`, '--assistant-viewport-top': `${viewport.offsetTop}px` }
    : {}
}
watch(() => props.mobile, updateViewport)
watch(() => props.confirmClear, async (value) => {
  await nextTick()
  if (value) confirmEl.value?.querySelector<HTMLButtonElement>('button')?.focus()
  else dialogEl.value?.querySelector<HTMLButtonElement>('.assistant-clear-action')?.focus()
})
watch(() => props.open, updateViewport)
onMounted(() => {
  updateViewport()
  window.visualViewport?.addEventListener('resize', updateViewport)
  window.visualViewport?.addEventListener('scroll', updateViewport)
})
onBeforeUnmount(() => {
  citationTrigger = null
  window.visualViewport?.removeEventListener('resize', updateViewport)
  window.visualViewport?.removeEventListener('scroll', updateViewport)
  setInert(false)
})
</script>
