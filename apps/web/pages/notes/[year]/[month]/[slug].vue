<template>
  <div
    v-if="article"
    class="article-reading"
    :class="{ 'article-reading--short': isShortArticle }"
    :data-article-variant="isShortArticle ? 'short' : 'long'"
  >
    <article class="article-reading-article">
      <div class="page-shell article-reading-shell">
      <nav class="article-back-bar" aria-label="返回文章">
        <NuxtLink to="/articles"><NavigationArrow direction="left" /> BACK TO ARTICLES <span class="sr-only">返回文章列表</span></NuxtLink>
      </nav>
      <header class="article-hero">
        <div class="article-hero-content">
          <p class="article-hero-meta">
            <NuxtLink
              v-if="article.category"
              class="status-chip chip-blue"
              :to="{ path: '/articles', query: { category: article.category.slug } }"
            >{{ article.category.name }}</NuxtLink>
            <span v-else class="status-chip chip-blue">工程笔记</span>
            <time :datetime="article.published_at">{{ publishedStamp }}</time>
            <span aria-hidden="true"> · </span>
            <span>{{ readingTime }} min read</span>
            <template v-if="showUpdatedDate">
              <span aria-hidden="true"> · </span>
              <span data-testid="article-updated-at">
                <span class="sr-only">最后更新 </span>Updated {{ updatedStamp }}
              </span>
            </template>
          </p>
          <h1 class="ee-heading article-hero-title">{{ article.title }}</h1>
          <p v-if="article.summary" class="article-hero-summary">{{ article.summary }}</p>
          <div v-if="article.tags.length" class="article-hero-tags" aria-label="文章标签">
            <NuxtLink v-for="tag in article.tags" :key="`hero-${tag.id}`" :to="{ path: '/articles', query: { tag: tag.slug } }">{{ tag.name }}</NuxtLink>
          </div>
          <div class="article-hero-toolbar">
            <div class="article-hero-actions">
              <a class="article-hero-primary" href="#article-body" data-testid="article-start-reading" @click.prevent="startReading">
                开始阅读 <span aria-hidden="true">↓</span>
              </a>
              <button
                class="article-hero-secondary"
                type="button"
                data-testid="article-copy-url"
                :disabled="copyState === 'copied'"
                @click="copyArticleUrl"
              >
                {{ copyState === 'copied' ? '已复制链接' : '复制文章链接' }}
              </button>
              <span class="sr-only" aria-live="polite">{{ copyAnnouncement }}</span>
            </div>
            <p v-if="leadFigure" class="article-hero-caption">
              图 01{{ leadFigure.alt ? ` · ${leadFigure.alt}` : '' }}
            </p>
          </div>
          <figure v-if="leadFigure" class="article-lead-figure" data-testid="article-lead-figure">
            <img :src="leadFigure.src" :alt="leadFigure.alt || ''">
          </figure>
        </div>
      </header>

      <ReadingLayout :headings="isShortArticle ? [] : headings" :reading-minutes="readingTime">
        <div id="article-body">
          <MarkdownArticle class="editorial-prose article-prose" :content="bodyContent" :wikilinks="article.wikilinks" copyable-code />
        </div>
      </ReadingLayout>

      <section
        v-if="article.references?.length"
        class="references-panel"
        data-testid="article-references"
      >
        <p class="eyebrow">References / 参考资料</p>
        <h2 class="ee-heading mt-3 text-2xl font-bold">继续查证</h2>
        <ol class="mt-5 grid gap-3">
          <li v-for="(reference, index) in article.references" :key="`${reference.url}-${index}`">
            <NuxtLink
              v-if="reference.url.startsWith('/')"
              class="reference-link"
              :to="reference.url"
            >
              <span class="ee-label">{{ String(index + 1).padStart(2, '0') }}</span>
              <span>{{ reference.display_title }}</span>
              <NavigationArrow />
            </NuxtLink>
            <a
              v-else
              class="reference-link"
              :href="reference.url"
              target="_blank"
              rel="noopener noreferrer"
            >
              <span class="ee-label">{{ String(index + 1).padStart(2, '0') }}</span>
              <span>{{ reference.display_title }}</span>
              <NavigationArrow direction="up-right" />
            </a>
          </li>
        </ol>
      </section>
      <BacklinkList :items="articleContext?.backlinks || []" />
      <nav
        v-if="articleContext?.previous || articleContext?.next"
        class="article-neighbor-nav"
        aria-label="相邻文章"
        data-testid="article-neighbors"
      >
        <NuxtLink v-if="articleContext.previous" :to="articleContext.previous.public_path" data-focus-card class="article-context-link">
          <span class="eyebrow">上一篇 / 更早</span>
          <strong>{{ articleContext.previous.title }}</strong>
        </NuxtLink>
        <span v-else aria-hidden="true" />
        <NuxtLink v-if="articleContext.next" :to="articleContext.next.public_path" data-focus-card class="article-context-link text-right">
          <span class="eyebrow">下一篇 / 更新</span>
          <strong>{{ articleContext.next.title }}</strong>
        </NuxtLink>
      </nav>
      </div>
      <section
        v-if="articleContext?.related.length"
        class="article-related-panel"
        aria-labelledby="related-articles-title"
        data-testid="related-articles"
      >
        <div class="page-shell article-related-inner">
          <p class="article-related-kicker">相关文章</p>
          <h2 id="related-articles-title" class="sr-only">相关文章</h2>
          <div class="article-related-grid" :data-count="articleContext.related.length">
            <NuxtLink
              v-for="related in articleContext.related"
              :key="related.id"
              :to="related.public_path"
              data-focus-card class="article-related-link"
            >
              <span class="article-related-next">{{ formatStamp(related.published_at) }}</span>
              <strong>{{ related.title }}</strong>
              <span v-if="related.summary">{{ related.summary }}</span>
            </NuxtLink>
          </div>
        </div>
      </section>
      <div class="page-shell article-reading-shell">
        <NuxtLink to="/articles" class="back-link"><NavigationArrow direction="left" /> 返回文章列表</NuxtLink>
      </div>
    </article>
  </div>
</template>

<script setup lang="ts">
import type { ArticleContext, PublicArticle } from '~/types/api'
import { articleDescription, extractLeadFigure, extractMarkdownHeadings, stripMatchingTitleHeading } from '~/utils/markdown'
import { readingMinutesFromContent } from '~/utils/readingTime'
import { absoluteSiteUrl } from '~/utils/site'

const route = useRoute()
const endpoint = '/articles/' + route.params.year + '/' + route.params.month + '/' + route.params.slug
const { data: article, error } = await useAsyncData('article-' + route.fullPath, () => apiFetch<PublicArticle>(endpoint))
useApiFailure(error, '文章不存在')
if (!article.value) throw createError({ statusCode: 502, statusMessage: '文章响应无效' })
const { data: articleContext, error: contextError } = await useAsyncData(
  'article-context-' + route.fullPath,
  () => apiFetch<ArticleContext>(`${endpoint}/context`),
)
useApiFailure(contextError)
const formatStamp = (value: string) => {
  const date = new Date(value)
  const month = String(date.getUTCMonth() + 1).padStart(2, '0')
  const day = String(date.getUTCDate()).padStart(2, '0')
  return `${date.getUTCFullYear()}.${month}.${day}`
}
const publishedStamp = computed(() => formatStamp(article.value!.published_at))
const updatedStamp = computed(() => formatStamp(article.value!.updated_at))
const showUpdatedDate = computed(() => (
  Date.parse(article.value!.updated_at) > Date.parse(article.value!.published_at)
))
const readingTime = computed(() => readingMinutesFromContent(article.value!.content))
const leadFigure = computed(() => extractLeadFigure(article.value!.content))
const bodyContent = computed(() => stripMatchingTitleHeading(
  leadFigure.value?.content ?? article.value!.content,
  article.value!.title,
))
const headings = computed(() => extractMarkdownHeadings(bodyContent.value)
  .filter(heading => heading.title !== article.value!.title))
const isShortArticle = computed(() => (
  readingTime.value <= 2
  && headings.value.length <= 1
  && !leadFigure.value
))
const description = computed(() => articleDescription(article.value!.summary, article.value!.content))
const config = useRuntimeConfig()
const articleUrl = computed(() => absoluteSiteUrl(config.public.siteUrl, article.value!.public_path))
const authorUrl = computed(() => absoluteSiteUrl(config.public.siteUrl, '/about'))
const publisherUrl = computed(() => absoluteSiteUrl(config.public.siteUrl, '/'))
const socialImageUrl = computed(() => absoluteSiteUrl(config.public.siteUrl, '/og/gavin-notes-default.png'))
const copyState = ref<'idle' | 'copied' | 'failed'>('idle')
const copyAnnouncement = computed(() => {
  if (copyState.value === 'copied') return '文章链接已复制'
  if (copyState.value === 'failed') return '无法复制，请手动复制地址栏链接'
  return ''
})

const startReading = () => {
  const first = headings.value[0]
  const target = first
    ? document.getElementById(first.slug)
    : document.getElementById('article-body')
  if (target && !target.hasAttribute('tabindex')) target.tabIndex = -1
  target?.focus({ preventScroll: true })
  target?.scrollIntoView({ behavior: prefersReducedMotion() ? 'auto' : 'smooth', block: 'start' })
}

const prefersReducedMotion = () =>
  import.meta.client && window.matchMedia('(prefers-reduced-motion: reduce)').matches

const copyArticleUrl = async () => {
  try {
    if (!navigator.clipboard?.writeText) throw new Error('clipboard unavailable')
    await navigator.clipboard.writeText(articleUrl.value)
    copyState.value = 'copied'
  }
  catch {
    copyState.value = 'failed'
  }
  window.setTimeout(() => { copyState.value = 'idle' }, 2000)
}

const syncReadingHeader = () => {
  if (!import.meta.client) return
  const root = document.documentElement
  root.dataset.articleReading = 'true'
  if (window.scrollY > 120) root.dataset.readingCompact = 'true'
  else delete root.dataset.readingCompact
}

onMounted(() => {
  syncReadingHeader()
  window.addEventListener('scroll', syncReadingHeader, { passive: true })
})

onUnmounted(() => {
  window.removeEventListener('scroll', syncReadingHeader)
  delete document.documentElement.dataset.articleReading
  delete document.documentElement.dataset.readingCompact
})

useSiteSeo(() => ({
  title: article.value?.title || '文章',
  description: description.value,
  canonicalPath: article.value?.public_path,
  ogType: 'article',
  publishedTime: article.value?.published_at,
  modifiedTime: article.value?.updated_at,
  tags: [article.value?.category?.name, ...(article.value?.tags.map(tag => tag.name) || [])].filter((value): value is string => Boolean(value)),
  jsonLd: article.value ? {
    '@context': 'https://schema.org',
    '@type': 'BlogPosting',
    headline: article.value.title,
    description: description.value,
    image: socialImageUrl.value,
    datePublished: article.value.published_at,
    dateModified: article.value.updated_at,
    inLanguage: 'zh-CN',
    author: { '@type': 'Person', name: 'Gavin', url: authorUrl.value },
    publisher: { '@type': 'Person', name: 'Gavin', url: publisherUrl.value },
    mainEntityOfPage: articleUrl.value,
    keywords: [article.value.category?.name, ...article.value.tags.map(tag => tag.name)].filter(Boolean),
  } : undefined,
}))
</script>

<style scoped>
:global(html:not(.dark)) .article-reading :deep(.article-code) {
  --hljs-keyword: #b42335;
}
</style>
