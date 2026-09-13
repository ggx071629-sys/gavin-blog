<template>
  <div v-if="project" class="page-shell editorial-detail public-detail project-detail">
    <article class="editorial-detail-article">
      <header class="public-detail-header">
        <nav class="detail-breadcrumb" aria-label="面包屑"><NuxtLink to="/projects">项目</NuxtLink><span aria-hidden="true"> / </span><span>项目详情</span></nav>
        <h1 class="ee-heading editorial-detail-title">{{ project.title }}</h1>
        <p v-if="project.summary" class="editorial-detail-summary">{{ project.summary }}</p>
        <div class="detail-meta">
          <time :datetime="project.published_at">{{ publishedDate }}</time>
          <span v-if="project.related_articles.length">{{ project.related_articles.length }} 篇关联笔记</span>
          <a v-if="project.repository_url" :href="project.repository_url" target="_blank" rel="noreferrer">代码仓库 <NavigationArrow direction="up-right" /></a>
          <a v-if="project.website_url" :href="project.website_url" target="_blank" rel="noreferrer">访问站点 <NavigationArrow direction="up-right" /></a>
        </div>
      </header>
      <ReadingLayout :headings="headings" :reading-minutes="readingTime">
          <MarkdownArticle class="editorial-prose" :content="bodyContent" :wikilinks="project.wikilinks" copyable-code />
          <section v-if="project.related_articles.length" class="references-panel">
            <p class="eyebrow">Related notes</p>
            <h2 class="ee-heading mt-3 text-2xl font-bold">关联文章</h2>
            <div class="mt-6 grid gap-3 sm:grid-cols-2">
              <NuxtLink
                v-for="(article, index) in project.related_articles"
                :key="article.id"
                :to="article.public_path"
                data-focus-card class="related-note"
              >
                <span class="ee-label">{{ String(index + 1).padStart(2, '0') }}</span>
                <h3 class="ee-heading mt-4 font-bold">{{ article.title }}</h3>
                <p class="mt-2 line-clamp-2 text-sm leading-6 text-[var(--ee-ink-muted)]">{{ article.summary }}</p>
              </NuxtLink>
            </div>
          </section>
          <BacklinkList :items="project.backlinks" />
          <NuxtLink to="/projects" class="back-link"><NavigationArrow direction="left" /> 返回项目列表</NuxtLink>
      </ReadingLayout>
    </article>
  </div>
</template>

<script setup lang="ts">
import type { PublicProject } from '~/types/api'
import { extractMarkdownHeadings, stripMatchingTitleHeading } from '~/utils/markdown'
import { readingMinutesFromContent } from '~/utils/readingTime'
import { absoluteSiteUrl } from '~/utils/site'

const route = useRoute()
const config = useRuntimeConfig()
const { data: project, error } = await useAsyncData(`project-${route.params.slug}`, () => apiFetch<PublicProject>(`/projects/${route.params.slug}`))
useApiFailure(error, '项目不存在')
if (!project.value) throw createError({ statusCode: 502, statusMessage: '项目响应无效' })
const bodyContent = computed(() => stripMatchingTitleHeading(project.value!.content, project.value!.title))
const headings = computed(() => extractMarkdownHeadings(bodyContent.value))
const readingTime = computed(() => readingMinutesFromContent(project.value!.content))
const publishedDate = computed(() => new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(project.value!.published_at)))

useSiteSeo(() => ({
  title: project.value?.title || '项目',
  description: project.value?.summary || 'Gavin 的项目实践。',
  canonicalPath: project.value?.public_path,
  publishedTime: project.value?.published_at,
  modifiedTime: project.value?.updated_at,
  jsonLd: project.value ? {
    '@context': 'https://schema.org',
    '@type': 'CreativeWork',
    name: project.value.title,
    description: project.value.summary,
    datePublished: project.value.published_at,
    dateModified: project.value.updated_at,
    inLanguage: 'zh-CN',
    author: { '@type': 'Person', name: 'Gavin' },
    url: absoluteSiteUrl(config.public.siteUrl, project.value.public_path),
    sameAs: [project.value.repository_url, project.value.website_url].filter(Boolean),
  } : undefined,
}))
</script>
