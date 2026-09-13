<template>
  <section class="admin-form-page writing-page" aria-labelledby="new-project-title">
    <NuxtLink to="/admin/projects" class="admin-back-link"><NavigationArrow direction="left" /> 返回项目</NuxtLink>
    <header class="writing-create-header"><div><p class="admin-page-kicker">内容 / 项目 / 新建</p><h1 id="new-project-title" class="admin-page-title">新建项目</h1><p class="admin-page-description">记录项目边界、链接、关联文章与 Markdown 正文。</p></div><button class="button-primary" type="submit" form="writing-create" data-testid="create-project" :disabled="!hydrated || submitting">{{ submitting ? '创建中…' : '创建项目草稿' }}</button></header>
    <form id="writing-create" class="admin-form-panel" novalidate @submit.prevent.self="create">
      <p v-if="errorMessage" role="alert" class="admin-form-error">{{ errorMessage }}</p>
      <WritingWorkspace ref="workspace">
        <template #title>
      <label class="field"><span>项目名称</span><input v-model="form.title" data-testid="new-project-title" placeholder="输入项目名称" maxlength="180" required @input="syncSlug"></label>
</template>
        <template #body><MarkdownMediaField v-model="form.content" test-id="new-project-content" /></template>
        <template #settings>
      <section class="studio-settings-group" aria-label="摘要与链接"><h3>摘要与链接</h3>
      <label class="field"><span>Slug</span><input v-model="form.slug" data-testid="new-project-slug" maxlength="160" required pattern="[a-z0-9]+(?:-[a-z0-9]+)*" @input="slugTouched = true"></label>
      <label class="field"><span>摘要</span><textarea v-model="form.summary" rows="3" maxlength="320" /></label>
      </section>
      <section class="studio-settings-group" aria-label="项目地址"><h3>项目地址</h3><label class="field"><span>仓库 URL</span><input v-model="form.repository_url" type="url" pattern="https?://.+"></label><label class="field"><span>站点 URL</span><input v-model="form.website_url" type="url" pattern="https?://.+"></label></section>
      <fieldset class="field studio-settings-group"><legend>关联文章</legend><div class="admin-choice-group admin-choice-group-grid"><label v-for="article in articles || []" :key="article.id" class="admin-choice"><input v-model="form.article_ids" type="checkbox" :value="article.id" :data-testid="`project-article-${article.slug}`"><span>{{ article.title }}</span></label><span v-if="!articles?.length" class="admin-empty-note">尚无文章。</span></div></fieldset>
</template>
        <template #preview><MarkdownArticle :content="form.content" /></template>
      </WritingWorkspace>
    </form>
  </section>
</template>

<script setup lang="ts">
import WritingWorkspace from '~/components/WritingWorkspace.vue'
import type { Article, Project } from '~/types/api'
import { apiErrorStatus } from '~/utils/api-errors'
import { slugify } from '~/utils/article'
import { fetchAllPages } from '~/utils/pagination'
definePageMeta({ layout: 'admin-core', middleware: 'admin' })
const workspace = ref<InstanceType<typeof WritingWorkspace> | null>(null)
const form = reactive({ title: '', slug: '', summary: '', content: '# 项目\n\n记录目标、约束与结果。', repository_url: '', website_url: '', article_ids: [] as number[] })
const { created } = useNewDraftSafety(() => form)
const slugTouched = ref(false)
const submitting = ref(false)
const errorMessage = ref('')
const hydrated = ref(false)
const { data: articles, error: articlesError } = await useAsyncData('project-article-options', () =>
  fetchAllPages<Article>((limit, offset) =>
    apiFetch<Article[]>(`/admin/articles?limit=${limit}&offset=${offset}`),
  ),
)
useApiFailure(articlesError)
const syncSlug = () => { if (!slugTouched.value) form.slug = slugify(form.title) }
onMounted(() => { hydrated.value = true })
const create = async () => {
  if (submitting.value) return
  if (!await workspace.value?.validate()) return
  submitting.value = true; errorMessage.value = ''
  try {
    const project = await apiFetch<Project>('/admin/projects', { method: 'POST', body: { ...form, repository_url: form.repository_url || null, website_url: form.website_url || null } })
    created.value = true; await navigateTo(`/admin/projects/${project.id}/edit`)
  }
  catch (error) {
    errorMessage.value = apiErrorStatus(error) === 409
      ? '这个 Slug 已被使用，请换一个。'
      : '创建失败，内容仍保留。请检查设置和网络后重试。'
    if (apiErrorStatus(error) === 409) await workspace.value?.reveal('[data-testid="new-project-slug"]')
  }
  finally { submitting.value = false }
}
useSeoMeta({ title: '新建项目' })
</script>
