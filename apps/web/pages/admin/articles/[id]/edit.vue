<template>
  <ArticleEditor v-if="article" :article="article" @saved="article = $event" />
</template>

<script setup lang="ts">
import type { Article } from '~/types/api'

definePageMeta({ layout: 'admin-core', middleware: 'admin' })
const route = useRoute()
const { data: article, error } = await useAsyncData(
  'admin-article-' + route.params.id,
  () => apiFetch<Article>('/admin/articles/' + route.params.id),
)
useApiFailure(error, '文章不存在')
useSeoMeta({ title: () => article.value?.title || '编辑文章' })
</script>
