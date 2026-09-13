<template>
  <section class="page-shell public-page articles-index max-w-4xl mx-auto space-y-8">
    <PublicPageHero
      class="articles-intro"
      label="文章笔记"
      artwork="articles"
      title="开发过程与问题排查"
      description="这里记录工具配置、开发实践和排障过程。可以按分类或标签，找到你关心的问题。"
    />

    <div v-if="taxonomyDegraded" class="articles-taxonomy-error" data-testid="taxonomy-degraded" role="status">
      栏目筛选暂不可用
    </div>
    <div v-else data-focus-card class="articles-filters">
      <nav class="articles-category-strip" aria-label="栏目筛选" data-testid="articles-category-strip">
        <NuxtLink
          to="/articles"
          class="articles-filter-link"
          :data-active="!route.query.category && !route.query.tag"
        >
          全部 {{ totalArticles }}
        </NuxtLink>
        <NuxtLink
          v-for="category in taxonomy?.categories || []"
          :key="category.id"
          :to="{ path: '/articles', query: { category: category.slug } }"
          class="articles-filter-link"
          :data-active="route.query.category === category.slug"
        >
          {{ category.name }} {{ category.article_count }}
        </NuxtLink>
      </nav>
      <div v-if="taxonomy?.tags.length" class="articles-tag-row" aria-label="标签筛选">
        <span class="articles-tags-label">标签 / TAGS</span>
        <NuxtLink
          v-for="tag in taxonomy.tags"
          :key="tag.id"
          :to="{ path: '/articles', query: { tag: tag.slug } }"
          class="filter-chip"
          :data-active="route.query.tag === tag.slug"
        >
          {{ tag.name }}
        </NuxtLink>
      </div>
      <NuxtLink to="/search" class="filter-search articles-search-link">
        <span aria-hidden="true">⌕</span>
        <span>搜索全部内容</span>
      </NuxtLink>
    </div>

    <div class="articles-results min-w-0" data-testid="articles-results" :aria-busy="listBusy ? 'true' : 'false'">
      <div v-if="articles.length" class="articles-list">
        <ArticleCard
          v-for="(article, index) in articles"
          :key="article.id"
          :article="article"
          :index="index + ((page - 1) * pageSize)"
          variant="list"
        />
      </div>
      <div v-else-if="!listBusy" data-focus-card class="empty-state" data-testid="articles-empty">暂时还没有符合条件的已发布文章。</div>
      <p v-if="listBusy" class="public-loading" role="status">正在读取内容…</p>
      <PaginationNav :page="page" :has-next="hasNext" path="/articles" :query="filters" />
    </div>
  </section>
</template>

<script setup lang="ts">
import type { PublicArticle, PublicTaxonomy } from '~/types/api'
import { paginatedApiPath, paginationWindow } from '~/utils/pagination'

const route = useRoute()
const pageSize = 12
const queryValue = (value: typeof route.query.category) => Array.isArray(value) ? value[0] : value
const filters = computed(() => ({
  category: queryValue(route.query.category) || undefined,
  tag: queryValue(route.query.tag) || undefined,
}))
const page = useBoundedPage(pageSize)
const endpoint = computed(() => paginatedApiPath('/articles', page.value, pageSize, filters.value))
const { data: articleRows, pending, error: articlesError } = await useAsyncData(
  'articles',
  (_nuxtApp, { signal }) => apiFetch<PublicArticle[]>(endpoint.value, { signal }),
  { watch: [endpoint] },
)
useApiFailure(articlesError)
const window = computed(() => paginationWindow(articleRows.value, pageSize))
const articles = computed(() => window.value.items)
const hasNext = computed(() => window.value.hasNext)
const listBusy = computed(() => Boolean(pending.value))
const { data: taxonomy, error: taxonomyError } = await useAsyncData('public-taxonomy', () => apiFetch<PublicTaxonomy>('/taxonomy'))
const taxonomyDegraded = computed(() => Boolean(taxonomyError.value))
const totalArticles = computed(() => taxonomy.value?.total_article_count ?? 0)

useSiteSeo(() => ({
  title: '文章',
  description: '工具配置、开发实践与问题排查笔记，可按分类和标签浏览。',
  jsonLd: {
    '@context': 'https://schema.org',
    '@type': 'CollectionPage',
    name: '文章',
    description: '工具配置、开发实践与问题排查笔记，可按分类和标签浏览。',
    inLanguage: 'zh-CN',
  },
}))
</script>
