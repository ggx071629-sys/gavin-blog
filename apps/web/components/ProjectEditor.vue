<template>
  <section class="writing-page studio-content-editor space-y-5">
    <NuxtLink class="admin-back-link" to="/admin/projects"><NavigationArrow direction="left" /> 返回列表</NuxtLink>
    <header class="admin-editor-header">
      <div>
        <p class="admin-page-kicker">内容 / 项目 #{{ current.id }}</p>
        <h1 class="admin-page-title">编辑项目</h1>
        <p class="admin-page-description">记录目标、约束与成果，更新发布后才会对访客可见。</p>
      </div>
      <div class="admin-editor-actions">
        <span class="save-state" :data-state="saveState" aria-live="polite">{{ stateLabel }}</span>
        <span v-if="current.status === 'published'" class="admin-attention-badge">工作副本 · 更新发布后公开</span>
        <button
          type="button"
          class="button-primary"
          data-testid="publish-project"
          :disabled="publishing || saveState === 'conflict'"
          @click="publish"
        >
          {{ publishing ? '发布中…' : current.status === 'published' ? '更新发布' : '发布项目' }}
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

    <WritingWorkspace ref="workspace" data-testid="project-editor-grid">
      <template #title>
        <label class="field"><span>项目名称</span><input v-model="form.title" data-testid="project-title" placeholder="输入项目名称" maxlength="180" required></label>

      </template>
      <template #body><div data-testid="project-editor-form">        <MarkdownMediaField v-model="form.content" test-id="project-content" /></div></template>
      <template #settings>
        <section class="studio-settings-group" aria-label="摘要与链接">
          <h3>摘要与链接</h3>
        <label class="field"><span>Slug</span><input v-model="form.slug" data-testid="project-slug" maxlength="160" required pattern="[a-z0-9]+(?:-[a-z0-9]+)*" :disabled="current.status === 'published'"></label>
        <label class="field"><span>摘要</span><textarea v-model="form.summary" rows="3" maxlength="320" /></label>
        </section>
        <section class="studio-settings-group" aria-label="项目地址">
          <h3>项目地址</h3>
          <label class="field"><span>仓库 URL</span><input v-model="form.repository_url" type="url" pattern="https?://.+" placeholder="https://github.com/…"></label>
          <label class="field"><span>站点 URL</span><input v-model="form.website_url" type="url" pattern="https?://.+" placeholder="https://…"></label>
        </section>
        <fieldset class="field studio-settings-group">
          <legend>关联文章</legend>
          <div class="admin-choice-group admin-choice-group-grid">
            <label v-for="article in articles" :key="article.id" class="admin-choice">
              <input v-model="form.article_ids" type="checkbox" :value="article.id">
              <span>{{ article.title }}</span>
              <span class="admin-version">{{ article.status === 'published' ? '已发布' : '草稿' }}</span>
            </label>
            <span v-if="!articles.length" class="admin-empty-note">尚无文章。</span>
          </div>
        </fieldset>
</template>
      <template #preview><div data-testid="project-editor-preview"><MarkdownArticle :content="form.content" /></div></template>
    </WritingWorkspace>
    <StudioPublishConfirmation ref="publication" />
  </section>
</template>

<script setup lang="ts">
import StudioPublishConfirmation from '~/components/StudioPublishConfirmation.vue'
import WritingWorkspace from '~/components/WritingWorkspace.vue'
import type { Article, Project } from '~/types/api'
import { apiErrorDetail, isOptimisticLockConflict } from '~/utils/api-errors'
import { AutosaveQueue, type AutosaveState } from '~/utils/autosave'
import { missingImageAltLocation } from '~/utils/markdown-media'

const props = defineProps<{ project: Project; articles: Article[] }>()
const emit = defineEmits<{ saved: [project: Project] }>()
const workspace = ref<InstanceType<typeof WritingWorkspace> | null>(null)
const publication = ref<InstanceType<typeof StudioPublishConfirmation> | null>(null)
const current = ref({ ...props.project })
const form = reactive({
  title: props.project.title,
  slug: props.project.slug,
  summary: props.project.summary,
  content: props.project.content,
  repository_url: props.project.repository_url || '',
  website_url: props.project.website_url || '',
  article_ids: [...props.project.article_ids],
})
const saveState = ref<AutosaveState>('idle')
const publishing = ref(false)
const publishError = ref('')

const save = async (snapshot: typeof form) => {
  if (!await workspace.value?.validate(false)) throw new Error('请检查必填字段与内容设置。')
  const body = {
    ...snapshot,
    repository_url: snapshot.repository_url || null,
    website_url: snapshot.website_url || null,
    article_ids: [...snapshot.article_ids],
    version: current.value.version,
  }
  const updated = await apiFetch<Project>(`/admin/projects/${current.value.id}`, { method: 'PATCH', body })
  current.value = updated
  emit('saved', updated)
}
const queue = new AutosaveQueue(save, state => { saveState.value = state })
const { flushBeforeNavigation: flushBeforeAction } = useAutosaveSafety(queue, () => { void workspace.value?.focusInvalid() })
watch(form, value => queue.schedule({ ...value, article_ids: [...value.article_ids] }), { deep: true })
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
      await workspace.value?.reveal('[data-testid="project-content"]')
      return
    }
    if (!await flushBeforeAction()) return
    if (!await publication.value?.request(current.value.status === 'published')) {
      publishing.value = false
      await nextTick()
      trigger?.focus()
      return
    }
    const updated = await apiFetch<Project>(`/admin/projects/${current.value.id}/publish`, {
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
