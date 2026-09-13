<template>
  <nav v-if="headings.length" class="content-toc" aria-label="文章目录">
    <div data-focus-card class="content-toc-desktop">
      <p class="content-toc-kicker">本页目录</p>
      <ol class="content-toc-list">
        <li v-for="heading in headings" :key="heading.slug" :class="{ 'content-toc-child': heading.level === 3 }">
          <a
            :href="`#${encodeURIComponent(heading.slug)}`"
            class="content-toc-link"
            :aria-current="heading.slug === activeSlug ? 'location' : undefined"
            :data-active="heading.slug === activeSlug ? 'true' : undefined"
            @click="navigateHeading"
          >
            {{ heading.title }}
          </a>
        </li>
      </ol>
      <div class="content-toc-progress" aria-live="polite">
        <p class="content-toc-progress-kicker">阅读进度</p>
        <p>{{ progressLabel }}</p>
      </div>
    </div>

    <details data-focus-card class="content-toc-disclosure">
      <summary class="content-toc-summary">
        <span>本页目录 · {{ activeIndex }} / {{ headings.length }}</span>
        <span aria-hidden="true">⌄</span>
      </summary>
      <ol class="content-toc-list">
        <li v-for="(heading, index) in headings" :key="`mobile-${heading.slug}-${index}`">
          <a
            :href="`#${encodeURIComponent(heading.slug)}`"
            class="content-toc-link"
            :data-active="heading.slug === activeSlug ? 'true' : undefined"
            @click="navigateHeading"
          >
            {{ heading.title }}
          </a>
        </li>
      </ol>
    </details>
  </nav>
</template>

<script setup lang="ts">
import type { MarkdownHeading } from '~/utils/markdown'

const props = withDefaults(defineProps<{
  headings: MarkdownHeading[]
  readingMinutes?: number
}>(), {
  readingMinutes: 1,
})

const activeSlug = ref(props.headings[0]?.slug || '')
const progress = ref(0)

const activeIndex = computed(() => {
  const index = props.headings.findIndex(heading => heading.slug === activeSlug.value)
  return index >= 0 ? index + 1 : 1
})

const remainingMinutes = computed(() => {
  const leftover = Math.ceil(props.readingMinutes * (1 - progress.value))
  return Math.max(progress.value >= 1 ? 0 : 1, leftover)
})

const progressLabel = computed(() => {
  const percent = Math.round(progress.value * 100)
  if (progress.value >= 1) return `${percent}% · 已读完`
  return `${percent}% · 约 ${remainingMinutes.value} 分钟`
})

const navigateHeading = (event: Event) => {
  const link = event.currentTarget as HTMLAnchorElement | null
  const target = link?.hash ? document.getElementById(decodeURIComponent(link.hash.slice(1))) : null
  if (target) {
    target.tabIndex = -1
    target.focus({ preventScroll: true })
  }
  const details = (event.currentTarget as HTMLElement | null)?.closest('details')
  if (details) details.open = false
}

const updateFromScroll = () => {
  if (!import.meta.client) return
  const body = document.querySelector<HTMLElement>('[data-article-body]')
  if (body) {
    const top = window.scrollY + body.getBoundingClientRect().top
    const span = Math.max(1, body.offsetHeight - window.innerHeight * 0.6)
    progress.value = Math.min(1, Math.max(0, (window.scrollY - top + 48) / span))
  }

  const marker = window.innerHeight * 0.28
  let current = props.headings[0]?.slug || ''
  for (const heading of props.headings) {
    const element = document.getElementById(heading.slug)
    if (!element) continue
    if (element.getBoundingClientRect().top <= marker) current = heading.slug
  }
  if (current) activeSlug.value = current
}

onMounted(() => {
  updateFromScroll()
  window.addEventListener('scroll', updateFromScroll, { passive: true })
  window.addEventListener('resize', updateFromScroll)
})

onUnmounted(() => {
  window.removeEventListener('scroll', updateFromScroll)
  window.removeEventListener('resize', updateFromScroll)
})

watch(() => props.headings.map(heading => heading.slug).join('|'), () => {
  activeSlug.value = props.headings[0]?.slug || ''
  updateFromScroll()
})
</script>
