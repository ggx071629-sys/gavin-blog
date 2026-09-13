<template><ProjectEditor v-if="project && articles" :project="project" :articles="articles" @saved="project = $event" /></template>
<script setup lang="ts">
import type { Article, Project } from '~/types/api'
import { fetchAllPages } from '~/utils/pagination'
definePageMeta({ layout: 'admin-core', middleware: 'admin' })
const route = useRoute()
const { data: project, error: projectError } = await useAsyncData(`admin-project-${route.params.id}`, () => apiFetch<Project>(`/admin/projects/${route.params.id}`))
const { data: articles, error: articlesError } = await useAsyncData('project-article-options', () =>
  fetchAllPages<Article>((limit, offset) =>
    apiFetch<Article[]>(`/admin/articles?limit=${limit}&offset=${offset}`),
  ),
)
useApiFailure(projectError, '项目不存在')
useApiFailure(articlesError)
useSeoMeta({ title: () => project.value?.title || '编辑项目' })
</script>
