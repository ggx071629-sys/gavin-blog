<template>
  <section class="writing-page studio-content-editor space-y-5">
    <NuxtLink class="admin-back-link" to="/admin/books"><NavigationArrow direction="left" /> 返回列表</NuxtLink>
    <header class="admin-editor-header">
      <div>
        <p class="admin-page-kicker">内容 / 读书笔记 #{{ current.id }}</p>
        <h1 class="admin-page-title">编辑读书笔记</h1>
        <p class="admin-page-description">记录阅读中的想法，更新发布后才会对访客可见。</p>
      </div>
      <div class="admin-editor-actions">
        <span class="save-state" :data-state="saveState" aria-live="polite">{{ stateLabel }}</span>
        <span v-if="current.status === 'published'" class="admin-attention-badge">工作副本 · 更新发布后公开</span>
        <button type="button" class="button-primary" data-testid="publish-book" :disabled="publishing || saveState === 'conflict'" @click="publish">
          {{ publishing ? '发布中…' : current.status === 'published' ? '更新发布' : '发布笔记' }}
        </button>
      </div>
    </header>

    <div v-if="saveState === 'conflict'" role="alert" class="admin-conflict-alert">
      服务器上已有更新。请先复制当前正文，再刷新并合并，避免丢失本地修改。
    </div>
    <p v-if="publishError" class="text-sm text-ee-danger-ink" role="alert">{{ publishError }}</p>

    <div v-if="saveState === 'error'" class="admin-feedback admin-feedback-error" role="alert">
      保存失败，修改仍留在当前页面。检查字段或网络后重试；保存成功前无法离开或发布。
      <button class="button-secondary" type="button" @click="retrySave">重试保存</button>
    </div>

    <WritingWorkspace ref="workspace" data-testid="book-editor-grid">
      <template #title>
        <label class="field"><span>书名</span><input v-model="form.book_title" data-testid="book-title" placeholder="输入书名" maxlength="180" required></label>
      </template>
      <template #body><div data-testid="book-editor-form"><MarkdownMediaField v-model="form.content" test-id="book-content" /></div></template>
      <template #settings>
        <label class="field"><span>作者</span><input v-model="form.author" data-testid="book-author" maxlength="180" required></label>
        <section class="studio-settings-group" aria-label="阅读记录">
          <h3>阅读记录</h3>
          <label class="field"><span>阅读状态</span><select v-model="form.reading_status" data-testid="book-reading-status"><option value="planned">想读</option><option value="reading">在读</option><option value="completed">读完</option><option value="paused">暂停</option></select></label>
          <label class="field"><span>阅读日期</span><input v-model="form.reading_date" type="date"></label>
          <label class="field"><span>评分</span><select v-model="form.rating"><option :value="null">未评分</option><option v-for="score in 5" :key="score" :value="score">{{ score }} / 5</option></select></label>
        </section>
        <section class="studio-settings-group" aria-label="书籍封面">
          <h3>书籍封面</h3>
          <label class="field">
            <span>封面 URL</span>
            <input
              v-model="form.cover_url"
              data-testid="book-cover-url"
              type="text"
              inputmode="url"
              :pattern="COVER_URL_PATTERN"
              :data-writing-error="COVER_URL_MESSAGE"
              placeholder="https://… 或媒体库地址"
            >
          </label>
          <p class="text-sm text-ee-ink-muted">也可从已有媒体中选择封面。</p>
          <MediaUploader library-only @selected="selectCover" />
        </section>
        <section class="studio-settings-group" aria-label="摘要与链接">
          <h3>摘要与链接</h3>
          <label class="field"><span>摘要</span><textarea v-model="form.summary" rows="3" maxlength="320" /></label>
          <label class="field"><span>Slug</span><input v-model="form.slug" data-testid="book-slug" maxlength="160" required pattern="[a-z0-9]+(?:-[a-z0-9]+)*" :disabled="current.status === 'published'"></label>
        </section>
      </template>
      <template #preview><div data-testid="book-editor-preview"><MarkdownArticle :content="form.content" /></div></template>
    </WritingWorkspace>
    <StudioPublishConfirmation ref="publication" />
  </section>
</template>

<script setup lang="ts">
import StudioPublishConfirmation from '~/components/StudioPublishConfirmation.vue'
import WritingWorkspace from '~/components/WritingWorkspace.vue'
import type { BookNote, ReadingStatus } from '~/types/api'
import { apiErrorDetail, isOptimisticLockConflict } from '~/utils/api-errors'
import { AutosaveQueue, type AutosaveState } from '~/utils/autosave'
import { missingImageAltLocation } from '~/utils/markdown-media'

const props = defineProps<{ note: BookNote }>()
const emit = defineEmits<{ saved: [note: BookNote] }>()
const workspace = ref<InstanceType<typeof WritingWorkspace> | null>(null)
const publication = ref<InstanceType<typeof StudioPublishConfirmation> | null>(null)
const current = ref({ ...props.note })
const form = reactive({
  book_title: props.note.book_title,
  author: props.note.author,
  slug: props.note.slug,
  cover_url: props.note.cover_url || '',
  reading_status: props.note.reading_status as ReadingStatus,
  reading_date: props.note.reading_date || '',
  rating: props.note.rating,
  summary: props.note.summary,
  content: props.note.content,
})
const saveState = ref<AutosaveState>('idle')
const publishing = ref(false)
const publishError = ref('')
// 媒体库返回站内相对地址；封面同时接受完整的 http(s) 图片地址。
const COVER_URL_PATTERN = '(https?://.+|/api/v1/media/[1-9][0-9]*/(webp|avif))'
const COVER_URL_MESSAGE = '请填写 http(s):// 图片地址，或从媒体库选择站内封面。'
const selectCover = (url: string) => { form.cover_url = url }
const save = async (snapshot: typeof form) => {
  if (!await workspace.value?.validate(false)) throw new Error('请检查必填字段与内容设置。')
  const updated = await apiFetch<BookNote>(`/admin/books/${current.value.id}`, {
    method: 'PATCH',
    body: { ...snapshot, cover_url: snapshot.cover_url || null, reading_date: snapshot.reading_date || null, version: current.value.version },
  })
  current.value = updated
  emit('saved', updated)
}
const queue = new AutosaveQueue(save, state => { saveState.value = state })
const { flushBeforeNavigation: flushBeforeAction } = useAutosaveSafety(queue, () => { void workspace.value?.focusInvalid() })
watch(form, value => queue.schedule({ ...value }), { deep: true })
const retrySave = async () => {
  if (await workspace.value?.validate()) await flushBeforeAction()
}
const stateLabel = computed(() => ({ idle: '尚未修改', pending: '等待保存', saving: '保存中…', saved: '已自动保存', error: '保存失败', conflict: '内容冲突' })[saveState.value])
const publish = async () => {
  if (publishing.value) return
  const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null
  publishing.value = true
  try {
    publishError.value = ''
    if (!await workspace.value?.validate()) return
    const missingAlt = missingImageAltLocation(form.content)
    if (missingAlt) {
      publishError.value = `第 ${missingAlt.line} 行、第 ${missingAlt.column} 列的图片缺少 Alt 文本，补齐后才能发布。`
      await workspace.value?.reveal('[data-testid="book-content"]')
      return
    }
    if (!await flushBeforeAction()) return
    if (!await publication.value?.request(current.value.status === 'published')) {
      publishing.value = false
      await nextTick()
      trigger?.focus()
      return
    }
    const updated = await apiFetch<BookNote>(`/admin/books/${current.value.id}/publish`, {
      method: 'POST',
      body: { version: current.value.version },
    })
    current.value = updated
    emit('saved', updated)
    if (updated.public_path) await navigateTo(updated.public_path)
  }
  catch (error) {
    if (isOptimisticLockConflict(error)) {
      saveState.value = 'conflict'
      return
    }
    publishError.value = apiErrorDetail(error) || '发布失败，请稍后重试。'
  }
  finally { publishing.value = false }
}
</script>
