<template>
  <article v-if="variant === 'list'" data-focus-card class="article-list-row blueprint-card group" data-testid="article-card" data-variant="list">
    <BlueprintWatermark :value="displayIndex" />
    <div class="article-list-copy">
      <div class="article-list-topline">
        <span v-if="article.category" class="status-chip" :class="['chip-blue', 'chip-emerald', 'chip-amber'][index % 3]">{{ article.category.name }}</span>
        <div class="article-info-strip">
          <time :datetime="article.published_at" class="article-info-item">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="5" width="16" height="16" rx="3" /><path d="M8 3v4m8-4v4M4 11h16m-12 4h3m-3 3h6" /></svg>
            {{ formattedDate }}
          </time>
          <span class="article-info-item article-info-duration">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="8.5" /><path d="M12 7v5l3 2" /></svg>
            <span><strong>{{ readingTime }}</strong> min read</span>
          </span>
        </div>
      </div>
      <h2 class="article-list-title ee-heading"><NuxtLink :to="article.public_path">{{ article.title }}</NuxtLink></h2>
      <p class="article-list-summary line-clamp-2">{{ description }}</p>
      <div v-if="article.tags?.length" class="article-list-tags"><span v-for="tag in article.tags.slice(0, 3)" :key="tag.id" class="telemetry-pill">{{ tag.name }}</span></div>
    </div>
    <NuxtLink :to="article.public_path" class="article-list-arrow" :aria-label="`阅读：${article.title}`"><NavigationArrow /></NuxtLink>
  </article>
  <article
    v-else
    data-focus-card class="article-card blueprint-card group relative flex min-h-64 flex-col rounded-ee-soft p-6 overflow-hidden"
    :class="{ 'featured-card': featured }"
    data-testid="article-card"
    data-variant="card"
  >
    <div class="flex items-start justify-between gap-4">
      <div class="ee-label flex flex-wrap items-center gap-2">
        <time :datetime="article.published_at">{{ formattedDate }}</time>
        <span aria-hidden="true">/</span>
        <span class="telemetry-pill">{{ readingTime }} min</span>
      </div>
      <span class="article-card-index" aria-hidden="true">{{ displayIndex }}</span>
    </div>

    <div v-if="article.category || article.tags.length" class="mt-4 flex flex-wrap gap-2">
      <NuxtLink
        v-if="article.category"
        :to="{ path: '/articles', query: { category: article.category.slug } }"
        class="ee-label rounded bg-[var(--ee-surface-high)] px-2.5 py-1 text-[var(--ee-ink)] transition-colors hover:bg-[var(--ee-primary)] hover:text-white"
      >
        {{ article.category.name }}
      </NuxtLink>
      <NuxtLink
        v-for="tag in article.tags.slice(0, 2)"
        :key="tag.id"
        :to="{ path: '/articles', query: { tag: tag.slug } }"
        class="ee-label rounded border px-2 py-0.5 text-[var(--ee-ink-muted)] transition-colors hover:border-[var(--ee-primary)] hover:text-[var(--ee-primary-strong)]"
        style="border-color: var(--ee-line)"
      >
        {{ tag.name }}
      </NuxtLink>
    </div>

    <h2 class="ee-heading mt-5 text-2xl font-bold leading-tight tracking-[-0.025em] sm:text-3xl">
      <NuxtLink :to="article.public_path" class="transition-colors group-hover:text-[var(--ee-primary-strong)]">
        {{ article.title }}
      </NuxtLink>
    </h2>
    <p v-if="article.summary.trim()" class="mt-3 line-clamp-3 leading-7 text-[var(--ee-ink-muted)]">
      {{ article.summary }}
    </p>
    <div class="mt-auto flex items-center justify-between pt-6">
      <NuxtLink :to="article.public_path" class="ee-label flex items-center gap-1.5 text-[var(--ee-ink)] group-hover:text-[var(--ee-primary-strong)]">
        <span>阅读全文</span>
        <NavigationArrow />
      </NuxtLink>
    </div>
  </article>
</template>

<script setup lang="ts">
import type { PublicArticle } from '~/types/api'
import { readingMinutesFromContent } from '~/utils/readingTime'
import { articleDescription } from '~/utils/markdown'

const props = withDefaults(defineProps<{
  article: PublicArticle
  index?: number
  featured?: boolean
  variant?: 'card' | 'list'
}>(), {
  index: 0,
  featured: false,
  variant: 'card',
})

const published = computed(() => new Date(props.article.published_at))
const formattedDate = computed(() => published.value.toISOString().slice(0, 10))
const readingTime = computed(() => readingMinutesFromContent(props.article.content))
const description = computed(() => articleDescription(props.article.summary, props.article.content, 160))
const displayIndex = computed(() => String(props.index + 1).padStart(2, '0'))
</script>
