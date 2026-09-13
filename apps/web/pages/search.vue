<template>
  <section class="page-shell public-page search-stage" data-testid="search-stage">
    <div data-focus-card class="search-panel" data-testid="search-panel">
      <header class="search-hero space-y-6">
        <SectionHeading label="站内搜索" />
        <div class="search-hero-composition">
        <div class="space-y-3">
          <h1 class="ee-heading search-title font-black tracking-tight text-4xl sm:text-5xl text-[var(--ee-ink)]">搜索你想了解的内容</h1>
          <p class="search-intro text-base text-[var(--ee-ink-muted)]">输入关键词，查找文章、项目和读书笔记中的相关内容。</p>
        </div>
        <PageHeroArtwork kind="search" />
        </div>
        <form
          class="search-form"
          role="search"
          data-testid="search-form"
          :data-hydrated="hydrated"
          @submit.prevent="submit"
        >
          <label class="search-input-wrap">
            <span class="sr-only">搜索文章、项目和读书笔记</span>
            <span class="search-terminal-prefix" aria-hidden="true">&gt;</span>
            <input
              v-model="input"
              data-testid="search-input"
              maxlength="120"
              autocomplete="off"
              placeholder="搜索文章、项目和读书笔记…"
              @keydown.esc.prevent="clearQuery"
            >
            <span class="ee-label search-shortcut" aria-hidden="true">Esc 清空</span>
          </label>
          <button class="button-primary shrink-0" data-testid="search-submit" type="submit" :disabled="!hydrated || !input.trim()">搜索</button>
        </form>
        <div class="search-hero-meta">
          <div class="flex flex-wrap gap-2" data-testid="search-chips" aria-label="搜索范围">
            <span class="search-scope-item">文章</span>
            <span class="search-scope-item">项目</span>
            <span class="search-scope-item">读书</span>
          </div>
          <NuxtLink to="/" class="ee-label inline-flex min-h-11 items-center gap-2 hover:text-[var(--ee-primary-strong)]">
            关闭 <span aria-hidden="true">×</span>
          </NuxtLink>
        </div>
      </header>

      <div v-if="uiState !== 'idle'" class="search-body">
        <div class="search-results-header">
          <p class="ee-label" data-testid="search-count">{{ statusLabel }}</p>
          <p v-if="uiState === 'results'" class="ee-label">按相关度</p>
          <p v-else-if="uiState === 'empty'" class="ee-label">
            <button type="button" class="search-clear" @click="clearQuery">清空查询</button>
          </p>
        </div>

        <div
          v-if="uiState === 'loading'"
          data-focus-card class="search-state-row"
          data-testid="search-loading"
          aria-busy="true"
          aria-live="polite"
        >
          <span class="search-score ee-label">…</span>
          <div>
            <p class="sr-only">正在搜索</p>
            <p class="ee-heading text-2xl font-bold tracking-[-0.025em] sm:text-3xl">正在读取索引…</p>
            <p class="ee-label mt-2">匹配标题、摘要与正文</p>
            <p class="mt-4 leading-7 text-[var(--ee-ink-muted)]">正在搜索已发布内容，请稍候。</p>
          </div>
        </div>

        <div v-else-if="uiState === 'results'" class="search-results" data-testid="search-results">
          <article
            v-for="result in results"
            :key="`${result.content_type}-${result.content_id}`"
            data-focus-card class="search-result group"
          >
            <div class="search-result-top"><span class="status-chip" :class="result.content_type === 'article' ? 'chip-emerald' : 'chip-blue'">{{ typeLabel[result.content_type] }}</span><time :datetime="result.published_at">{{ formatDate(result.published_at) }}</time></div>
            <h2><NuxtLink :to="result.public_path">{{ result.title }}</NuxtLink></h2>
            <p class="search-result-snippet">{{ result.snippet || result.summary }}</p>
          </article>
        </div>

        <div
          v-else
          data-focus-card class="search-state-row"
          data-testid="search-empty"
        >
          <span class="search-score ee-label">空</span>
          <div>
            <p class="ee-heading text-2xl font-bold tracking-[-0.025em] sm:text-3xl">没有匹配内容</p>
            <p class="ee-label mt-2">试试更短或更具体的关键词</p>
            <p class="mt-4 leading-7 text-[var(--ee-ink-muted)]">搜索覆盖已发布文章、项目与读书笔记的标题、摘要和正文。</p>
          </div>
        </div>
      </div>
      <p
        v-else
        data-focus-card class="empty-state mt-9"
        data-testid="search-idle"
      >输入关键词开始搜索全部已发布内容。</p>

      <PaginationNav
        v-if="uiState === 'results' || (uiState !== 'loading' && page > 1)"
        :page="page"
        :has-next="hasNext"
        path="/search"
        :query="{ q: query }"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import SectionHeading from '~/components/SectionHeading.vue'
import PageHeroArtwork from '~/components/PageHeroArtwork.vue'
import type { ContentType, SearchResult } from '~/types/api'
import { paginatedApiPath, paginationWindow } from '~/utils/pagination'
import { searchUiState } from '~/utils/search-ui'

const route = useRoute()
const input = ref(typeof route.query.q === 'string' ? route.query.q : '')
const hydrated = ref(false)
const query = computed(() => typeof route.query.q === 'string' ? route.query.q.trim() : '')
const pageSize = 20
const page = useBoundedPage(pageSize)
const endpoint = computed(() => (
  query.value ? paginatedApiPath('/search', page.value, pageSize, { q: query.value }) : ''
))

const { data: resultRows, pending, error } = await useAsyncData(
  'site-search',
  (_nuxtApp, { signal }) => (
    query.value
      ? apiFetch<SearchResult[]>(endpoint.value, { signal })
      : Promise.resolve([] as SearchResult[])
  ),
  { watch: [endpoint], default: () => [] },
)
useApiFailure(error)
const isLoading = computed(() => Boolean(query.value && pending.value))
const window = computed(() => paginationWindow(isLoading.value ? [] : resultRows.value, pageSize))
const results = computed(() => window.value.items)
const hasNext = computed(() => window.value.hasNext)
const uiState = computed(() => searchUiState({
  query: query.value,
  pending: isLoading.value,
  itemCount: results.value.length,
}))
const statusLabel = computed(() => {
  if (uiState.value === 'loading') return '正在搜索索引'
  if (uiState.value === 'empty') return `0 条结果 / “${query.value}”`
  return `“${query.value}” / 本页 ${results.value.length} 条结果`
})
const typeLabel: Record<ContentType, string> = { article: '文章', project: '项目', book: '读书' }
const formatDate = (value: string) => new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(value))
const submit = () => navigateTo({ path: '/search', query: { q: input.value.trim() } })
const clearQuery = () => {
  input.value = ''
  return navigateTo({ path: '/search' })
}
onMounted(() => { hydrated.value = true })

useSiteSeo(() => ({
  title: '搜索',
  description: '搜索 Gavin 的文章、项目与读书笔记。',
  indexable: false,
}))
</script>

<style scoped>
.search-hero-composition {display:grid;grid-template-columns:minmax(0,1.5fr) minmax(180px,.65fr);align-items:center;gap:24px;}
.search-hero-composition .search-title {font-size:clamp(28px,2.8vw,38px);line-height:1.4;}
.search-hero-composition :deep(.page-artwork) {max-width:250px;}
@media(max-width:639px){.search-hero-composition{grid-template-columns:minmax(0,1fr);gap:12px;}.search-hero-composition :deep(.page-artwork){max-width:210px;justify-self:end;}.search-hero-composition .search-title{font-size:28px;}}
</style>
