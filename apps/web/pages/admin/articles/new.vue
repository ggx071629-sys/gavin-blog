<template>
  <section class="admin-form-page writing-page" aria-labelledby="new-article-title">
    <NuxtLink to="/admin/articles" class="admin-back-link"><NavigationArrow direction="left" /> 返回文章</NuxtLink>
    <header class="writing-create-header"><div>
      <p class="admin-page-kicker">内容 / 文章 / 新建</p>
      <h1 id="new-article-title" class="admin-page-title">新建草稿</h1>
      <p class="admin-page-description">先建立草稿，再进入编辑工作台自动保存与发布。</p>
    </div><button class="button-primary" type="submit" form="writing-create" data-testid="create-draft" :disabled="!hydrated || submitting">
          {{ submitting ? '创建中…' : '创建草稿' }}
        </button></header>
    <form id="writing-create" class="admin-form-panel" novalidate @submit.prevent.self="create">
      <p v-if="errorMessage" role="alert" class="admin-form-error">{{ errorMessage }}</p>
      <WritingWorkspace ref="workspace">
        <template #title>
      <label class="field">
        <span>标题</span>
        <input
          v-model="form.title"
          data-testid="new-title"
          placeholder="为文章写一个标题"
          maxlength="180"
          required
          :aria-invalid="Boolean(fieldErrors.title)"
          :aria-describedby="fieldErrors.title ? 'new-title-error' : undefined"
          @input="syncSlug"
        >
        <span
          v-if="fieldErrors.title"
          id="new-title-error"
          class="field-validation-error"
          role="alert"
        >{{ fieldErrors.title }}</span>
      </label>
</template>
        <template #body><MarkdownMediaField v-model="form.content" test-id="new-content" /></template>
        <template #settings>
<div class="grid gap-5 md:grid-cols-2">
        <label class="field">
          <span>栏目</span>
          <select v-model="form.category_id" data-testid="new-category">
            <option :value="null">未分类</option>
            <option v-for="category in categories || []" :key="category.id" :value="category.id">
              {{ category.name }}
            </option>
          </select>
        </label>
        <fieldset class="field">
          <legend>标签</legend>
          <div class="admin-choice-group">
            <label v-for="tag in tags || []" :key="tag.id" class="admin-choice">
              <input v-model="form.tag_ids" type="checkbox" :value="tag.id" :data-testid="`new-tag-${tag.slug}`">
              <span>{{ tag.name }}</span>
            </label>
            <span v-if="!tags?.length" class="admin-empty-note">尚无标签</span>
          </div>
        </fieldset>
      </div>
<section class="studio-settings-group" aria-label="摘要与链接"><h3>摘要与链接</h3>      <label class="field">
        <span>Slug</span>
        <input
          v-model="form.slug"
          data-testid="new-slug"
          maxlength="160"
          required
          pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
          :aria-invalid="Boolean(fieldErrors.slug)"
          :aria-describedby="fieldErrors.slug ? 'new-slug-error' : undefined"
          @input="onSlugInput"
        >
        <span
          v-if="fieldErrors.slug"
          id="new-slug-error"
          class="field-validation-error"
          role="alert"
        >{{ fieldErrors.slug }}</span>
      </label>
      <label class="field">
        <span>摘要</span>
        <textarea v-model="form.summary" rows="3" maxlength="320" />
      </label>
      </section>
</template>
        <template #preview><MarkdownArticle :content="form.content" /></template>
      </WritingWorkspace>
    </form>
  </section>
</template>

<script setup lang="ts">
import WritingWorkspace from '~/components/WritingWorkspace.vue'
import type { Article, TaxonomyItem } from '~/types/api'
import { slugify, validateArticleCreateFields } from '~/utils/article'
import { apiErrorDetail, apiErrorStatus } from '~/utils/api-errors'

definePageMeta({ layout: 'admin-core', middleware: 'admin' })
const workspace = ref<InstanceType<typeof WritingWorkspace> | null>(null)
const form = reactive({
  title: '',
  slug: '',
  summary: '',
  content: '# 新文章\n\n从这里开始写作。',
  category_id: null as number | null,
  tag_ids: [] as number[],
})
const { created } = useNewDraftSafety(() => form)
const slugTouched = ref(false)
const submitting = ref(false)
const errorMessage = ref('')
const fieldErrors = reactive({ title: '', slug: '' })
const hydrated = ref(false)
const { data: categories, error: categoriesError } = await useAsyncData('admin-categories', () =>
  apiFetch<TaxonomyItem[]>('/admin/categories'),
)
const { data: tags, error: tagsError } = await useAsyncData('admin-tags', () =>
  apiFetch<TaxonomyItem[]>('/admin/tags'),
)
useApiFailure(categoriesError)
useApiFailure(tagsError)

const syncSlug = () => {
  if (!slugTouched.value) form.slug = slugify(form.title)
  fieldErrors.title = ''
  fieldErrors.slug = ''
}
const onSlugInput = () => {
  slugTouched.value = true
  fieldErrors.slug = ''
}
onMounted(() => { hydrated.value = true })

const create = async () => {
  if (submitting.value) return
  errorMessage.value = ''
  Object.assign(fieldErrors, validateArticleCreateFields(form))
  if (fieldErrors.title || fieldErrors.slug) {
    await workspace.value?.reveal(fieldErrors.title ? '[data-testid="new-title"]' : '[data-testid="new-slug"]')
    return
  }
  if (!await workspace.value?.validate()) return

  submitting.value = true
  try {
    const article = await apiFetch<Article>('/admin/articles', {
      method: 'POST',
      body: form,
    })
    created.value = true; await navigateTo('/admin/articles/' + article.id + '/edit')
  }
  catch (error: unknown) {
    const status = apiErrorStatus(error)
    const detail = apiErrorDetail(error)
    if (status === 409 && detail === 'slug already exists') {
      fieldErrors.slug = '这个 Slug 已被使用，请换一个。'
      await workspace.value?.reveal('[data-testid="new-slug"]')
    }
    else if (status === 422 && detail === 'category does not exist') {
      errorMessage.value = '所选栏目已不存在，请刷新页面后重试。'
    }
    else if (status === 422 && detail === 'one or more tags do not exist') {
      errorMessage.value = '一个或多个所选标签已不存在，请刷新页面后重试。'
    }
    else {
      errorMessage.value = detail
        ? `无法创建草稿：${detail}`
        : '无法创建草稿，请稍后重试。'
    }
  }
  finally {
    submitting.value = false
  }
}
useSeoMeta({ title: '新建草稿' })
</script>
