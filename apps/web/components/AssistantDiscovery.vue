<template>
  <div v-show="available" ref="layer" class="assistant-orb-layer" :class="{ 'is-dragging': drag?.moved }">
    <button
      ref="ball" type="button" class="assistant-orb" data-testid="assistant-orb" data-assistant-entry="orb"
      :style="{ left: `${point.x}px`, top: `${point.y}px` }" aria-label="问 Gavin，悬浮助手"
      aria-describedby="assistant-orb-help" aria-haspopup="dialog" :aria-expanded="entry.open.value"
      aria-controls="ask-gavin-panel" @pointerdown="startDrag" @pointermove="moveDrag"
      @pointerup="endDrag" @pointercancel="cancelDrag" @lostpointercapture="cancelDrag"
      @click="activate" @keydown="moveWithKeyboard" @pointerenter="hovered = $event.pointerType === 'mouse'"
      @pointerleave="hovered = false" @focus="focused = true" @blur="focused = false">
      <span class="assistant-orb-float" aria-hidden="true">
        <span class="assistant-orb-glow" />
        <span class="assistant-orb-scroll" />
        <span class="assistant-orb-orbit"><i /></span>
        <span class="assistant-orb-orbit-inner"><i /></span>
        <span class="assistant-orb-core">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M5 4h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-6 3V6a2 2 0 0 1 2-2Z" stroke-linejoin="round"/><path d="M8 9h8M8 13h5" stroke-linecap="round"/></svg>
        </span>
        <span class="assistant-orb-spark">✦</span>
      </span>
    </button>
    <button
      type="button" class="assistant-orb-motion-toggle" :style="motionToggleStyle"
      :aria-label="motionPaused ? '播放悬浮球动效' : '暂停悬浮球动效'" :title="motionPaused ? '播放动效' : '暂停动效'"
      :aria-pressed="motionPaused" @click="toggleMotion">
      <svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true" fill="currentColor">
        <path v-if="motionPaused" d="m5 2 9 6-9 6Z" />
        <path v-else d="M4 3h3v10H4zm5 0h3v10H9z" />
      </svg>
    </button>
    <span id="assistant-orb-help" class="sr-only">拖动可调整位置，松手吸附左右边缘。也可用方向键移动，按回车打开助手。</span>
    <aside
      v-if="showHint && !entry.guidanceDismissed.value" ref="hint" class="assistant-orb-hint" data-testid="assistant-orb-hint"
      :style="hintStyle" aria-label="助手使用提示">
      <div class="assistant-orb-hint-heading"><strong>有问题，问 Gavin</strong><button type="button" aria-label="关闭使用提示" @click="dismissHint"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg></button></div>
      <p>想了解本站的项目或技术实践？可以问我。</p>
      <small>影响阅读？可以关闭这条提示。</small>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { clamp, orbPoint, snapOrb, parseOrbPosition, ORB_SIZE, ORB_POSITION_KEY, ORB_GUIDANCE_KEY } from '~/utils/assistant/orb'

const entry = useAssistantEntry()
const overlay = usePublicOverlay()
const route = useRoute()
const layer = ref<HTMLElement | null>(null)
const ball = ref<HTMLButtonElement | null>(null)
const hint = ref<HTMLElement | null>(null)
const ready = ref(false)
const pageVisible = ref(true)
const position = useState('assistant-orb-position', () => parseOrbPosition(null))
const dimensions = reactive({ width: 0, height: 0 })
const hintHeight = ref(150)
const drag = ref<{ id: number, startX: number, startY: number, x: number, y: number, moved: boolean } | null>(null)
const draggedPoint = ref({ x: 0, y: 0 })
const point = computed(() => drag.value?.moved ? draggedPoint.value : orbPoint(position.value, dimensions.width, dimensions.height))
const available = computed(() => ready.value && entry.visible.value && !entry.open.value && overlay.owner.value === null)
const showHint = ref(false)
const motionPaused = useState('assistant-orb-motion-paused', () => false)
const hovered = ref(false)
const focused = ref(false)
const motionKey = 'gavin:assistant-orb-motion-paused:v1'
let disposed = false
let motion: ReturnType<typeof import('~/utils/assistant/orb-motion')['createOrbMotion']> | undefined
const motionActive = computed(() => available.value && pageVisible.value && !motionPaused.value)
const engaged = computed(() => hovered.value || focused.value || drag.value !== null)
const motionToggleStyle = computed(() => ({
  left: `${clamp(point.value.x + (point.value.x > dimensions.width / 2 ? -52 : ORB_SIZE + 8), dimensions.width - 44)}px`,
  top: `${clamp(point.value.y + 4, dimensions.height - 44)}px`,
}))
const toggleMotion = () => {
  motionPaused.value = !motionPaused.value
  try { localStorage.setItem(motionKey, motionPaused.value ? '1' : '0') }
  catch { /* Keep the in-memory preference when storage is unavailable. */ }
}
watch(motionActive, value => motion?.setActive(value))
watch(engaged, value => motion?.setEngaged(value))
watch(() => route.fullPath, async () => { await nextTick(); motion?.refresh() })
let timer: ReturnType<typeof setTimeout> | undefined
let resizeObserver: ResizeObserver | undefined
let hintObserver: ResizeObserver | undefined
let suppressClick = false
const hintStyle = computed(() => {
  const width = Math.min(288, dimensions.width)
  const x = clamp(point.value.x + ORB_SIZE / 2 - width / 2, dimensions.width - width)
  const y = point.value.y >= hintHeight.value + 12 ? point.value.y - hintHeight.value - 12 : point.value.y + ORB_SIZE + 12
  return { left: `${x}px`, top: `${clamp(y, dimensions.height - hintHeight.value)}px`, width: `${width}px`, maxHeight: `${Math.max(0, dimensions.height - ORB_SIZE - 12)}px` }
})
const savePosition = () => {
  try { localStorage.setItem(ORB_POSITION_KEY, JSON.stringify(position.value)) }
  catch { /* Position remains valid for this visit. */ }
}
const measure = () => {
  if (!layer.value?.clientWidth || !layer.value.clientHeight) return
  drag.value = null
  dimensions.width = layer.value.clientWidth
  dimensions.height = layer.value.clientHeight
}
const resetHintTimer = () => {
  clearTimeout(timer)
  showHint.value = false
  if (!available.value || !pageVisible.value || entry.guidanceDismissed.value) return
  timer = setTimeout(() => { showHint.value = true }, 3000)
}
watch([available, pageVisible, entry.guidanceDismissed, () => route.fullPath], resetHintTimer)
watch(available, async value => { if (value) { await nextTick(); measure() } })
watch(hint, element => {
  hintObserver?.disconnect()
  if (element) {
    hintHeight.value = element.offsetHeight
    hintObserver = new ResizeObserver(() => { hintHeight.value = element.offsetHeight })
    hintObserver.observe(element)
  }
})
const dismissHint = () => {
  entry.finishGuidance()
  nextTick(() => ball.value?.focus({ preventScroll: true }))
}
const activate = (event: MouseEvent) => {
  if (suppressClick && event.detail !== 0) { suppressClick = false; return }
  suppressClick = false
  entry.activate('orb')
}
const startDrag = (event: PointerEvent) => {
  if (!event.isPrimary || event.button !== 0) return
  suppressClick = false
  drag.value = { id: event.pointerId, startX: event.clientX, startY: event.clientY, ...point.value, moved: false }
  ball.value?.setPointerCapture(event.pointerId)
}
const moveDrag = (event: PointerEvent) => {
  const current = drag.value
  if (!current || current.id !== event.pointerId) return
  const dx = event.clientX - current.startX, dy = event.clientY - current.startY
  if (!current.moved && Math.hypot(dx, dy) < 6) return
  current.moved = true
  draggedPoint.value = { x: clamp(current.x + dx, dimensions.width - ORB_SIZE), y: clamp(current.y + dy, dimensions.height - ORB_SIZE) }
}
const endDrag = (event: PointerEvent) => {
  if (!drag.value || drag.value.id !== event.pointerId) return
  const moved = drag.value.moved
  if (moved) {
    position.value = snapOrb(point.value.x, point.value.y, dimensions.width, dimensions.height)
    savePosition()
  }
  drag.value = null
  suppressClick = moved
  if (ball.value?.hasPointerCapture(event.pointerId)) ball.value.releasePointerCapture(event.pointerId)
}
const cancelDrag = () => {
  if (!drag.value) return
  suppressClick = drag.value.moved
  drag.value = null
}
const moveWithKeyboard = (event: KeyboardEvent) => {
  if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return
  event.preventDefault()
  const side = event.key === 'ArrowLeft' ? 'left' : event.key === 'ArrowRight' ? 'right' : position.value.side
  const delta = event.key === 'ArrowUp' ? -24 : event.key === 'ArrowDown' ? 24 : 0
  const travel = Math.max(1, dimensions.height - ORB_SIZE)
  position.value = { side, ratio: clamp(position.value.ratio + delta / travel, 1) }
  savePosition()
}
const onVisibility = () => { pageVisible.value = document.visibilityState === 'visible' }
onMounted(async () => {
  try {
    entry.guidanceDismissed.value ||= localStorage.getItem(ORB_GUIDANCE_KEY) === '1'
    const savedPosition = localStorage.getItem(ORB_POSITION_KEY)
    if (savedPosition !== null) position.value = parseOrbPosition(savedPosition)
    const savedMotion = localStorage.getItem(motionKey)
    if (savedMotion !== null) motionPaused.value = savedMotion === '1'
  }
  catch { /* Storage is optional; keep defaults or the existing in-memory state. */ }
  onVisibility()
  ready.value = true
  await nextTick()
  if (disposed) return
  measure()
  resizeObserver = new ResizeObserver(measure)
  if (layer.value) resizeObserver.observe(layer.value)
  document.addEventListener('visibilitychange', onVisibility)
  try {
    const { createOrbMotion } = await import('~/utils/assistant/orb-motion')
    if (disposed || !layer.value) return
    motion = createOrbMotion(layer.value)
    motion.setEngaged(engaged.value)
    motion.setActive(motionActive.value)
  }
  catch { /* A failed animation chunk must not prevent opening the assistant. */ }
})
onBeforeUnmount(() => {
  disposed = true
  motion?.destroy()
  clearTimeout(timer)
  resizeObserver?.disconnect()
  hintObserver?.disconnect()
  document.removeEventListener('visibilitychange', onVisibility)
})
</script>

<style scoped>
.assistant-orb-layer {position:fixed;inset:max(16px,env(safe-area-inset-top)) max(16px,env(safe-area-inset-right)) max(16px,env(safe-area-inset-bottom)) max(16px,env(safe-area-inset-left));z-index:40;pointer-events:none;}
.assistant-orb {position:absolute;display:grid;place-items:center;width:52px;height:52px;padding:0;border:0;border-radius:50%;background:transparent;color:var(--ee-accent-text);pointer-events:auto;touch-action:none;user-select:none;cursor:grab;isolation:isolate;}
.assistant-orb-float {position:absolute;inset:0;pointer-events:none;}
.assistant-orb-core {position:absolute;inset:2px;display:grid;place-items:center;border:1px solid rgb(255 255 255 / 65%);border-radius:50%;color:var(--ee-primary-contrast);background:radial-gradient(circle at 30% 20%,rgb(255 255 255 / 75%),transparent 37%),radial-gradient(circle at 68% 80%,color-mix(in srgb,var(--ee-primary) 45%,#080d29),var(--ee-primary) 70%);box-shadow:inset 0 -5px 9px rgb(0 0 0 / 18%),inset 0 2px 4px rgb(255 255 255 / 50%),0 5px 14px color-mix(in srgb,var(--ee-primary) 35%,transparent);}
.assistant-orb-core svg {filter:drop-shadow(0 1px 2px rgb(0 0 0 / 25%));}
.assistant-orb-glow {position:absolute;inset:-12px;border-radius:50%;opacity:.35;background:radial-gradient(circle,color-mix(in srgb,var(--ee-primary) 60%,transparent),transparent 70%);}
.assistant-orb-orbit,.assistant-orb-orbit-inner,.assistant-orb-scroll {position:absolute;inset:-6px;border:1px solid color-mix(in srgb,var(--ee-primary) 28%,transparent);border-radius:50%;}
.assistant-orb-orbit i {position:absolute;top:6px;left:6px;width:7px;height:7px;border:1px solid var(--ee-surface);border-radius:50%;background:var(--ee-primary);box-shadow:0 0 7px color-mix(in srgb,var(--ee-primary) 55%,transparent);}
.assistant-orb-orbit-inner {inset:-2px;border-color:transparent;}
.assistant-orb-orbit-inner i {position:absolute;right:0;bottom:9px;width:4px;height:4px;border-radius:50%;background:var(--ee-accent-text);}
.assistant-orb-scroll {inset:-10px;border:2px solid transparent;border-top-color:color-mix(in srgb,var(--ee-primary) 70%,transparent);border-bottom-color:color-mix(in srgb,var(--ee-primary) 25%,transparent);transform:rotate(-35deg);}
.assistant-orb-spark {position:absolute;right:1px;top:-7px;font:14px/1 sans-serif;color:var(--ee-accent-text);text-shadow:0 0 6px var(--ee-surface);}
.assistant-orb:hover .assistant-orb-core,.assistant-orb:focus-visible .assistant-orb-core {border-color:var(--ee-primary);}
.assistant-orb-motion-toggle {position:absolute;display:grid;place-items:center;width:44px;height:44px;padding:0;border:0;border-radius:50%;background:transparent;color:var(--ee-ink-muted);pointer-events:auto;}
.assistant-orb-motion-toggle::before {content:'';position:absolute;inset:8px;border:1px solid var(--ee-line);border-radius:50%;background:var(--ee-surface);box-shadow:0 2px 8px rgb(0 0 0 / 6%);z-index:-1;}
.assistant-orb-motion-toggle:hover {color:var(--ee-accent-text);}
.assistant-orb-motion-toggle:focus-visible {outline:2px solid var(--ee-focus);outline-offset:1px;}
@media (prefers-reduced-motion:reduce) {.assistant-orb-motion-toggle {display:none;}}
@media (forced-colors:active) {.assistant-orb-core {background:ButtonFace;color:ButtonText;border:2px solid ButtonText;}.assistant-orb-glow,.assistant-orb-spark,.assistant-orb-scroll,.assistant-orb-orbit,.assistant-orb-orbit-inner {display:none;}}
.is-dragging .assistant-orb {cursor:grabbing;}
.assistant-orb:focus-visible,.assistant-orb-hint button:focus-visible {outline:2px solid var(--ee-focus);outline-offset:3px;}
.assistant-orb-hint {position:absolute;box-sizing:border-box;overflow:auto;padding:12px 16px 16px;border:1px solid var(--ee-line);border-radius:14px;background:var(--ee-surface);color:var(--ee-ink);box-shadow:0 8px 24px rgb(0 0 0 / 12%);pointer-events:auto;}
.assistant-orb-hint-heading {display:flex;align-items:center;justify-content:space-between;gap:8px;}
.assistant-orb-hint strong {font:700 15px/1.5 var(--ee-heading);}
.assistant-orb-hint button {display:grid;place-items:center;width:44px;height:44px;flex-shrink:0;margin-right:-8px;border-radius:8px;color:var(--ee-ink-muted);}
.assistant-orb-hint button:hover {background:var(--ee-surface-low);}
.assistant-orb-hint p {font-size:14px;line-height:1.7;}
.assistant-orb-hint small {display:block;margin-top:8px;font-size:12px;line-height:1.6;color:var(--ee-ink-muted);}
</style>
