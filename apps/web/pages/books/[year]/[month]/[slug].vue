<template>
  <div v-if="note" class="page-shell editorial-detail public-detail book-detail">
    <article class="editorial-detail-article">
      <header class="public-detail-header book-detail-heading" :class="{ 'has-cover': note.cover_url }">
        <img v-if="note.cover_url" :src="note.cover_url" :alt="`${note.book_title} 封面`" class="book-real-cover">
        <div class="min-w-0">
          <nav class="detail-breadcrumb" aria-label="面包屑"><NuxtLink to="/books">读书</NuxtLink><span aria-hidden="true"> / </span><span>笔记</span></nav>
          <h1 class="ee-heading editorial-detail-title">{{ note.book_title }}</h1>
          <p v-if="note.author" class="book-detail-author">{{ note.author }}</p>
          <p v-if="note.summary" class="editorial-detail-summary">{{ note.summary }}</p>
          <div class="detail-meta">
            <span>{{ readingStatusLabel(note.reading_status) }}</span>
            <span v-if="note.rating">{{ ratingLabel(note.rating) }}</span>
            <time :datetime="note.published_at">发布于 {{ publishedDate }}</time>
            <span v-if="note.reading_date">阅读日期 {{ note.reading_date }}</span>
          </div>
        </div>
      </header>
      <ReadingLayout :headings="headings" :reading-minutes="readingTime">
        <MarkdownArticle class="editorial-prose" :content="bodyContent" :wikilinks="note.wikilinks" copyable-code />
        <BacklinkList :items="note.backlinks" />
        <NuxtLink to="/books" class="back-link"><NavigationArrow direction="left" /> 返回阅读索引</NuxtLink>
      </ReadingLayout>
    </article>
  </div>
</template>

<script setup lang="ts">
import type { PublicBookNote } from '~/types/api'
import { ratingLabel, readingStatusLabel } from '~/utils/content'
import { extractMarkdownHeadings, stripMatchingTitleHeading } from '~/utils/markdown'

import { readingMinutesFromContent } from '~/utils/readingTime'

const route = useRoute()
const endpoint = `/books/${route.params.year}/${route.params.month}/${route.params.slug}`
const { data: note, error } = await useAsyncData(`book-${route.fullPath}`, () => apiFetch<PublicBookNote>(endpoint))
useApiFailure(error, '读书笔记不存在')
if (!note.value) throw createError({ statusCode: 502, statusMessage: '读书笔记响应无效' })
const bodyContent = computed(() => stripMatchingTitleHeading(note.value!.content, note.value!.book_title))
const headings = computed(() => extractMarkdownHeadings(bodyContent.value))
const readingTime = computed(() => readingMinutesFromContent(note.value!.content))
const publishedDate = computed(() => new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(note.value!.published_at)))

useSiteSeo(() => ({
  title: note.value?.book_title || '读书笔记',
  description: note.value?.summary || 'Gavin 的读书笔记。',
  canonicalPath: note.value?.public_path,
  ogType: 'article',
  publishedTime: note.value?.published_at,
  modifiedTime: note.value?.updated_at,
  jsonLd: note.value ? {
    '@context': 'https://schema.org',
    '@type': 'Review',
    name: note.value.book_title,
    reviewBody: note.value.summary,
    datePublished: note.value.published_at,
    dateModified: note.value.updated_at,
    inLanguage: 'zh-CN',
    author: { '@type': 'Person', name: 'Gavin' },
    itemReviewed: {
      '@type': 'Book',
      name: note.value.book_title,
      author: { '@type': 'Person', name: note.value.author },
    },
    ...(note.value.rating ? {
      reviewRating: { '@type': 'Rating', ratingValue: note.value.rating, bestRating: 5, worstRating: 1 },
    } : {}),
  } : undefined,
}))
</script>
