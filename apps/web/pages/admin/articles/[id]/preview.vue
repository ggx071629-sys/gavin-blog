<template>
  <div v-if="article" class="admin-draft-preview studio-article-preview writing-page article-reading">
    <NuxtLink :to="'/admin/articles/' + article.id + '/edit'" class="admin-back-link"><NavigationArrow direction="left" /> 返回编辑</NuxtLink>
    <header class="admin-page-header studio-preview-header">
      <div><p class="admin-page-title">预览草稿</p><p class="admin-page-description">检查已保存的工作副本。需要发布时，请返回编辑并确认发布。</p></div>
      <NuxtLink :to="'/admin/articles/' + article.id + '/revisions'" class="button-secondary">版本历史</NuxtLink>
    </header>
    <div class="admin-draft-banner" role="status" data-testid="preview-banner">
      <span v-if="article.status === 'published'">
        <strong>已发布</strong><span aria-hidden="true"> · </span><span>工作副本预览，公开站点仍显示当前发布修订。</span>
      </span>
      <span v-else>
        <strong>未公开</strong><span aria-hidden="true"> · </span><span>草稿预览，不会出现在公开站点。</span>
      </span>
    </div>
    <article class="admin-draft-article">
      <header class="border-b pb-9 ee-rule">
        <p class="admin-page-kicker">{{ article.status === 'published' ? 'Working copy / 工作副本' : 'Draft preview / 草稿' }}</p>
        <h1 class="ee-heading mt-5 text-4xl font-bold tracking-[-0.04em] sm:text-5xl">{{ article.title }}</h1>
        <p v-if="article.summary" class="admin-secondary-text mt-6 text-xl leading-8">{{ article.summary }}</p>
      </header>
      <ReadingLayout :headings="headings">
        <MarkdownArticle class="editorial-prose article-prose mt-10" :content="bodyContent" :wikilinks="article.wikilinks" copyable-code />
      </ReadingLayout>
    </article>
  </div>
</template>

<script setup lang="ts">
import { extractMarkdownHeadings, stripMatchingTitleHeading } from '~/utils/markdown'
import type { Article } from '~/types/api'

definePageMeta({ layout: 'admin-core', middleware: 'admin' })
const route = useRoute()
const { data: article, error } = await useAsyncData(
  'preview-' + route.params.id,
  () => apiFetch<Article>('/admin/articles/' + route.params.id),
)
useApiFailure(error, '文章不存在')
const bodyContent = computed(() => stripMatchingTitleHeading(article.value?.content || '', article.value?.title || ''))
const headings = computed(() => extractMarkdownHeadings(bodyContent.value))
useSeoMeta({ robots: 'noindex, nofollow', title: () => '预览：' + (article.value?.title || '文章') })
</script>
