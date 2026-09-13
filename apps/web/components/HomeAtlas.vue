<template>
  <section data-focus-card class="home-atlas knowledge-route" data-testid="home-atlas" aria-label="知识领域图谱" :aria-busy="pending">
    <p v-if="pending && !content" class="atlas-message" role="status" data-testid="home-loading">正在读取知识路线…</p>
    <template v-if="content">
      <div v-if="content.topics.length" ref="mapElement" class="knowledge-map">
        <svg class="knowledge-lines" aria-hidden="true">
          <g v-for="line in routeLines" :key="line.id" :data-active="rootEngaged || active === line.id">
            <path :d="line.path" />
            <path :d="line.path" class="knowledge-line-active" />
          </g>
        </svg>
        <button data-focus-card class="knowledge-root" type="button" aria-label="我的笔记，查看全部知识路线" @pointerenter="rootHovered = $event.pointerType === 'mouse'" @pointerleave="rootHovered = false" @focus="rootFocused = true" @blur="rootFocused = false" @click="reset">
          <svg class="knowledge-book" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
            <path class="knowledge-book-outline" pathLength="1" d="M12 6C9 3.5 5.5 3.5 3 4.5V19C6 18 9 18.5 12 21C15 18.5 18 18 21 19V4.5C18.5 3.5 15 3.5 12 6Z" stroke-linejoin="round" />
            <path class="knowledge-book-spine" pathLength="1" d="M12 6V21" stroke-linecap="round" />
            <path class="knowledge-book-text" pathLength="1" d="M6 8L9 9M6 11L9 12M15 9L18 8M15 12L18 11" stroke-linecap="round" />
          </svg>
          <strong>我的笔记</strong>
        </button>
        <div class="knowledge-paths">
          <div v-for="topic in content.topics" :key="topic.category.id" class="knowledge-path" :data-active="active === topic.category.id" :data-muted="active !== null && active !== topic.category.id" data-testid="atlas-branch" @pointerenter="hovered = $event.pointerType === 'mouse' ? topic.category.id : null" @pointermove="moveGlow" @pointerleave="hovered = null" @focusin="focused = topic.category.id" @focusout="onFocusOut">
            <div class="knowledge-topic">
              <button type="button" data-focus-card class="knowledge-node" :aria-pressed="selected === topic.category.id" data-testid="atlas-node" @click="selected = selected === topic.category.id ? null : topic.category.id">
                <strong>{{ topic.category.name }}</strong><span>{{ topic.category.article_count }} 篇笔记</span>
              </button>
              <NuxtLink class="knowledge-category" :to="{ path: '/articles', query: { category: topic.category.slug } }" :aria-label="`浏览${topic.category.name}栏目`">浏览领域 <NavigationArrow direction="up-right" /></NuxtLink>
            </div>
            <div class="knowledge-connector" aria-hidden="true" />
            <NuxtLink v-if="topic.article" :to="topic.article.public_path" data-focus-card class="knowledge-article" data-testid="atlas-article">
              <span class="knowledge-note-label">最新笔记<span v-if="topic.article.readingMinutes"> · {{ topic.article.readingMinutes }} 分钟</span></span>
              <strong>{{ topic.article.title }}</strong>
              <span class="knowledge-read">阅读笔记 <NavigationArrow direction="up-right" /></span>
            </NuxtLink>
            <div v-else data-focus-card class="knowledge-missing" :data-testid="`atlas-${topic.state}`"><p>{{ topic.state === 'error' ? '这条路线的笔记暂不可用' : '这条路线等待新的笔记' }}</p><button v-if="topic.state === 'error'" type="button" :disabled="pending" @click="$emit('retry')">{{ pending ? '读取中…' : '重试读取' }}</button></div>
          </div>
        </div>
      </div>
      <div v-else class="atlas-message" :data-testid="content.taxonomyFailed ? 'atlas-unavailable' : 'atlas-fallback'">
        <p>{{ content.taxonomyFailed ? '知识路线暂时无法读取。' : content.articles.length ? '领域还在整理，从最近一篇开始。' : '新的笔记，慢慢连接。' }}</p>
        <NuxtLink v-if="content.articles[0]" :to="content.articles[0].public_path" class="atlas-fallback-article">{{ content.articles[0].title }} <NavigationArrow direction="up-right" /></NuxtLink>
        <button v-if="content.taxonomyFailed" type="button" :disabled="pending" @click="$emit('retry')">{{ pending ? '读取中…' : '重试读取' }}</button>
      </div>
      <footer class="knowledge-footer">
        <p role="status" data-testid="atlas-selection">{{ selectedTopic ? `沿着「${selectedTopic.category.name}」继续探索` : '选择一个领域，点亮它的知识路线' }}</p>
        <button v-if="selected !== null" type="button" @click="reset">查看全部路线</button>
        <NuxtLink v-else-if="content.categoryCount && content.categoryCount > 3" to="/articles" data-testid="atlas-all-categories">更多领域 <NavigationArrow direction="up-right" /></NuxtLink>
      </footer>
    </template>
  </section>
</template>

<script setup lang="ts">
import type { HomeContent } from '~/utils/home'

const props = defineProps<{ content: HomeContent | null | undefined, pending: boolean }>()
defineEmits<{ retry: [] }>()
const mapElement = ref<HTMLElement | null>(null)
const routeLines = ref<{ id: number; path: string }[]>([])
let resizeObserver: ResizeObserver | undefined
let frame = 0
let glowFrame = 0
const moveGlow = (event: PointerEvent) => {
  if (event.pointerType !== 'mouse' || !window.matchMedia('(hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)').matches) return
  const branch = event.currentTarget as HTMLElement
  const { clientX, clientY } = event
  cancelAnimationFrame(glowFrame)
  glowFrame = requestAnimationFrame(() => {
    const bounds = branch.getBoundingClientRect()
    branch.style.setProperty('--route-pointer-x', `${clientX - bounds.left}px`)
    branch.style.setProperty('--route-pointer-y', `${clientY - bounds.top}px`)
  })
}
const measureRoutes = () => {
  const map = mapElement.value
  const root = map?.querySelector('.knowledge-root')
  if (!map || !root) { routeLines.value = []; return }
  const origin = map.getBoundingClientRect()
  const box = (element: Element) => {
    const rect = element.getBoundingClientRect()
    return { x: rect.left - origin.left, y: rect.top - origin.top, width: rect.width, height: rect.height }
  }
  const start = box(root)
  const stackedRoot = window.matchMedia('(max-width: 1279px)').matches
  const stackedNotes = window.matchMedia('(max-width: 639px)').matches
  routeLines.value = Array.from(map.querySelectorAll('.knowledge-path')).flatMap((branch, index) => {
    const node = branch.querySelector('.knowledge-node')
    const note = branch.querySelector('.knowledge-article, .knowledge-missing')
    const topic = props.content?.topics[index]
    if (!node || !note || !topic) return []
    const target = box(node)
    const end = box(note)
    const targetY = target.y + target.height / 2
    let path: string
    if (stackedRoot) {
      const x = start.x + 12
      const y = start.y + start.height
      const radius = Math.min(12, (target.x - x) / 2, (targetY - y) / 2)
      path = `M ${x} ${y} V ${targetY - radius} Q ${x} ${targetY} ${x + radius} ${targetY} H ${target.x}`
    }
    else {
      const x = start.x + start.width
      const y = start.y + start.height / 2
      const middle = (x + target.x) / 2
      path = `M ${x} ${y} C ${middle} ${y} ${middle} ${targetY} ${target.x} ${targetY}`
    }
    if (stackedNotes) {
      const x = target.x + Math.min(24, target.width / 2)
      path += ` M ${x} ${target.y + target.height} V ${end.y}`
    }
    else {
      const x = target.x + target.width
      const endY = end.y + end.height / 2
      const middle = (x + end.x) / 2
      path += ` M ${x} ${targetY} C ${middle} ${targetY} ${middle} ${endY} ${end.x} ${endY}`
    }
    return [{ id: topic.category.id, path }]
  })
}
const scheduleMeasurement = () => {
  cancelAnimationFrame(frame)
  frame = requestAnimationFrame(measureRoutes)
}
const observeMap = async () => {
  await nextTick()
  resizeObserver?.disconnect()
  const map = mapElement.value
  if (map) {
    resizeObserver?.observe(map)
    map.querySelectorAll('.knowledge-root, .knowledge-node, .knowledge-article, .knowledge-missing').forEach(element => resizeObserver?.observe(element))
  }
  scheduleMeasurement()
}
onMounted(() => {
  resizeObserver = new ResizeObserver(scheduleMeasurement)
  void observeMap()
  window.addEventListener('resize', scheduleMeasurement)
})
watch(() => props.content, () => { if (import.meta.client) void observeMap() })
onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  cancelAnimationFrame(frame)
  window.removeEventListener('resize', scheduleMeasurement)
  cancelAnimationFrame(glowFrame)
})
const selected = ref<number | null>(null)
const rootHovered = ref(false)
const rootFocused = ref(false)
const rootEngaged = computed(() => rootHovered.value || rootFocused.value)
const hovered = ref<number | null>(null)
const focused = ref<number | null>(null)
const active = computed(() => hovered.value ?? focused.value ?? selected.value)
const selectedTopic = computed(() => props.content?.topics.find(topic => topic.category.id === selected.value))
const onFocusOut = (event: FocusEvent) => { if (!(event.currentTarget as HTMLElement).contains(event.relatedTarget as Node | null)) focused.value = null }
const reset = () => { selected.value = null; hovered.value = null; focused.value = null }
watch(() => props.content, reset)
</script>
