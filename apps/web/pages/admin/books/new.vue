<template>
  <section class="admin-form-page writing-page" aria-labelledby="new-book-title">
    <NuxtLink to="/admin/books" class="admin-back-link"><NavigationArrow direction="left" /> 返回读书笔记</NuxtLink><header class="writing-create-header"><div><p class="admin-page-kicker">内容 / 读书 / 新建</p><h1 id="new-book-title" class="admin-page-title">新建读书笔记</h1><p class="admin-page-description">建立书籍元数据与笔记草稿，后续在编辑工作台自动保存。</p></div><button class="button-primary" type="submit" form="writing-create" data-testid="create-book" :disabled="!hydrated || submitting">{{ submitting ? '创建中…' : '创建笔记草稿' }}</button></header>
    <form id="writing-create" class="admin-form-panel" novalidate @submit.prevent.self="create">
      <p v-if="errorMessage" role="alert" class="admin-form-error">{{ errorMessage }}</p>
      <WritingWorkspace ref="workspace">
        <template #title><label class="field"><span>书名</span><input v-model="form.book_title" data-testid="new-book-title" placeholder="输入书名" maxlength="180" required @input="syncSlug"></label></template>
        <template #body><MarkdownMediaField v-model="form.content" test-id="new-book-content" /></template>
      <template #settings>
        <label class="field"><span>作者</span><input v-model="form.author" data-testid="new-book-author" maxlength="180" required></label>
        <section class="studio-settings-group" aria-label="阅读记录">
          <h3>阅读记录</h3>
          <label class="field"><span>阅读状态</span><select v-model="form.reading_status" data-testid="new-book-reading-status"><option value="planned">想读</option><option value="reading">在读</option><option value="completed">读完</option><option value="paused">暂停</option></select></label>
          <label class="field"><span>阅读日期</span><input v-model="form.reading_date" type="date"></label>
          <label class="field"><span>评分</span><select v-model="form.rating"><option :value="null">未评分</option><option v-for="score in 5" :key="score" :value="score">{{ score }} / 5</option></select></label>
        </section>
        <section class="studio-settings-group" aria-label="书籍封面">
          <h3>书籍封面</h3>
          <label class="field">
            <span>封面 URL</span>
            <input
              v-model="form.cover_url"
              data-testid="new-book-cover-url"
              type="text"
              inputmode="url"
              :pattern="COVER_URL_PATTERN"
              :data-writing-error="COVER_URL_MESSAGE"
              placeholder="https://… 或媒体库地址"
            >
          </label>
          <p class="text-sm text-ee-ink-muted">也可从已有媒体中选择封面。</p>
          <MediaUploader library-only @selected="form.cover_url = $event" />
        </section>
        <section class="studio-settings-group" aria-label="摘要与链接">
          <h3>摘要与链接</h3>
          <label class="field"><span>摘要</span><textarea v-model="form.summary" rows="3" maxlength="320" /></label>
          <label class="field"><span>Slug</span><input v-model="form.slug" data-testid="new-book-slug" maxlength="160" required pattern="[a-z0-9]+(?:-[a-z0-9]+)*" @input="slugTouched = true"></label>
        </section>
      </template>
        <template #preview><MarkdownArticle :content="form.content" /></template>
      </WritingWorkspace>
    </form>
  </section>
</template>
<script setup lang="ts">
import WritingWorkspace from '~/components/WritingWorkspace.vue'
import type { BookNote, ReadingStatus } from '~/types/api'
import { apiErrorStatus } from '~/utils/api-errors'
import { slugify } from '~/utils/article'
definePageMeta({ layout: 'admin-core', middleware: 'admin' })
const workspace = ref<InstanceType<typeof WritingWorkspace> | null>(null)
const form = reactive({ book_title: '', author: '', slug: '', cover_url: '', reading_status: 'planned' as ReadingStatus, reading_date: '', rating: null as number | null, summary: '', content: '# 读书笔记\n\n记录观点、证据与行动。' })
const { created } = useNewDraftSafety(() => form)
// 与 BookNoteEditor 保持同一封面地址契约：完整 http(s) URL 或站内媒体库地址。
const COVER_URL_PATTERN = '(https?://.+|/api/v1/media/[1-9][0-9]*/(webp|avif))'
const COVER_URL_MESSAGE = '请填写 http(s):// 图片地址，或从媒体库选择站内封面。'
const slugTouched = ref(false); const submitting = ref(false); const errorMessage = ref('')
const hydrated = ref(false)
const syncSlug = () => { if (!slugTouched.value) form.slug = slugify(form.book_title) }
onMounted(() => { hydrated.value = true })
const create = async () => {
  if (submitting.value) return
  if (!await workspace.value?.validate()) return
  submitting.value = true; errorMessage.value = ''
  try { const note = await apiFetch<BookNote>('/admin/books', { method: 'POST', body: { ...form, cover_url: form.cover_url || null, reading_date: form.reading_date || null } }); created.value = true; await navigateTo(`/admin/books/${note.id}/edit`) }
  catch (error) {
    errorMessage.value = apiErrorStatus(error) === 409
      ? '这个 Slug 已被使用，请换一个。'
      : '创建失败，内容仍保留。请检查设置和网络后重试。'
    if (apiErrorStatus(error) === 409) await workspace.value?.reveal('[data-testid="new-book-slug"]')
  }
  finally { submitting.value = false }
}
useSeoMeta({ title: '新建读书笔记' })
</script>
