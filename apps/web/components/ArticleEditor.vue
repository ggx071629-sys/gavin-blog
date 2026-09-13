<template>
  <section class="writing-page studio-content-editor space-y-5">
    <NuxtLink class="admin-back-link" to="/admin/articles"><NavigationArrow direction="left" /> 返回列表</NuxtLink>
    <header class="admin-editor-header">
      <div>
        <p class="admin-page-kicker">内容 / 文章 #{{ current.id }}</p>
        <h1 class="admin-page-title">编辑文章</h1>
        <p class="admin-page-description">正在编辑工作副本，更新发布后才会对访客可见。</p>
      </div>
      <div class="admin-editor-actions">
        <span class="save-state" :data-state="saveState" aria-live="polite">{{ stateLabel }}</span>
        <span
          v-if="current.status === 'published'"
          class="status-chip admin-status"
          data-testid="publish-revision"
        >
          发布 #{{ current.current_publish_revision ?? '—' }}
          <template v-if="current.has_unpublished_changes"> · 有未发布修改</template>
        </span>
        <NuxtLink
          class="button-secondary"
          :to="'/admin/articles/' + current.id + '/preview'"
        >
          预览
        </NuxtLink>
        <NuxtLink
          v-if="current.status === 'published'"
          class="button-secondary"
          :to="'/admin/articles/' + current.id + '/revisions'"
          data-testid="open-revisions"
        >
          版本历史
        </NuxtLink>
        <button
          type="button"
          class="button-primary"
          data-testid="publish"
          :disabled="publishing || saveState === 'conflict'"
          @click="publish"
        >
          {{ publishing ? '发布中…' : current.status === 'published' ? '更新发布' : '发布' }}
        </button>
      </div>
    </header>

    <div
      v-if="saveState === 'conflict'"
      role="alert"
      class="admin-conflict-alert"
    >
      服务器上已有更新。请先复制当前正文，再刷新并合并，避免丢失本地修改。
    </div>
    <p v-if="publishError" class="text-sm text-ee-danger-ink" role="alert">{{ publishError }}</p>

    <div v-if="saveState === 'error'" class="admin-feedback admin-feedback-error" role="alert">
      保存失败，修改仍留在当前页面。检查字段或网络后重试；保存成功前无法离开或发布。
      <button class="button-secondary" type="button" @click="retrySave">重试保存</button>
    </div>

    <WritingWorkspace ref="workspace" data-testid="article-editor-grid">
      <template #title>
        <label class="field">
          <span>标题</span>
          <input v-model="form.title" data-testid="title" placeholder="为文章写一个标题" maxlength="180" required>
        </label>

      </template>
      <template #body><div data-testid="article-editor-form">        <div>
          <p class="mb-2 text-sm leading-5 text-[var(--ee-ink-muted)]">
            公开页标题已经是一级标题；正文可从 <code>#</code> 开始组织，预览与公开页会整体下移一级。
            使用 <code>[[slug]]</code> 或 <code>[[article:slug|显示名]]</code> 链接已发布内容。
          </p>
          <MarkdownMediaField v-model="form.content" test-id="content" min-height-class="min-h-[34rem]" />
        </div>
</div></template>
      <template #settings>
<div class="grid gap-4 md:grid-cols-2">
          <label class="field">
            <span>栏目</span>
            <select v-model="form.category_id" data-testid="category">
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
                <input v-model="form.tag_ids" type="checkbox" :value="tag.id" :data-testid="`tag-${tag.slug}`">
                <span>{{ tag.name }}</span>
              </label>
              <span v-if="!tags?.length" class="admin-empty-note">
                请先在“栏目与标签”中创建标签。
              </span>
            </div>
          </fieldset>
        </div>
        <section class="studio-settings-group" aria-label="摘要与链接"><h3>摘要与链接</h3><div class="grid gap-4 md:grid-cols-2">
          <label class="field">
            <span>Slug</span>
            <input
              v-model="form.slug"
              data-testid="slug"
              maxlength="160" required pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
              :disabled="current.status === 'published'"
            >
          </label>
          <label class="field">
            <span>摘要</span>
            <input v-model="form.summary" data-testid="summary" maxlength="320">
          </label>
        </div>
        </section>
<fieldset class="field" data-testid="article-references">
          <legend>参考资料</legend>
          <p class="admin-empty-note">工作副本参考资料只在发布后出现在公开页，并生成反链。</p>
          <p v-if="incompleteReferenceIndex >= 0" class="admin-form-error" role="status">有参考资料尚未填完，这些条目尚未保存。请补齐或移除后再离开或发布。</p>
          <div v-for="(item, index) in form.references" :key="index" class="mt-3 grid gap-2 border p-3" style="border-color: var(--ee-line)">
            <div class="grid gap-2 md:grid-cols-[8rem_1fr_auto]">
              <label class="field">
                <span>类型</span>
                <select v-model="item.kind" :data-testid="`reference-kind-${index}`">
                  <option value="internal">站内</option>
                  <option value="external">外部</option>
                </select>
              </label>
              <label class="field">
                <span>标题</span>
                <input v-model="item.display_title" maxlength="180" :data-testid="`reference-title-${index}`">
              </label>
              <button class="button-secondary self-end" type="button" :data-testid="`reference-remove-${index}`" @click="form.references.splice(index, 1)">
                移除
              </button>
            </div>
            <label v-if="item.kind === 'external'" class="field">
              <span>HTTPS URL</span>
              <input v-model="item.url" type="url" pattern="https?://.+" :data-testid="`reference-url-${index}`" placeholder="https://">
            </label>
            <div v-else class="grid gap-2 md:grid-cols-2">
              <label class="field">
                <span>目标类型</span>
                <select v-model="item.target_type" :data-testid="`reference-target-type-${index}`">
                  <option value="article">文章</option>
                  <option value="project">项目</option>
                  <option value="book">读书</option>
                </select>
              </label>
              <label class="field">
                <span>已发布目标</span>
                <select :value="item.target_id ?? ''" :data-testid="`reference-target-${index}`" @change="assignInternalTarget(item, ($event.target as HTMLSelectElement).value)">
                  <option value="">选择…</option>
                  <option v-for="target in targetsFor(item.target_type)" :key="`${target.type}-${target.id}`" :value="target.id">
                    {{ target.title }}
                  </option>
                </select>
              </label>
            </div>
          </div>
          <button class="button-secondary mt-3" type="button" data-testid="reference-add" :disabled="form.references.length >= 20" @click="addReference">
            添加参考资料
          </button>
        </fieldset></template>
      <template #preview><div data-testid="article-editor-preview"><MarkdownArticle :content="form.content" :wikilinks="current.wikilinks" /></div></template>
    </WritingWorkspace>
    <StudioPublishConfirmation ref="publication" />
  </section>
</template>

<script setup lang="ts">
import WritingWorkspace from '~/components/WritingWorkspace.vue'
import StudioPublishConfirmation from '~/components/StudioPublishConfirmation.vue'
import { onBeforeRouteLeave } from 'vue-router'
import type { Article, ArticleReference, ContentType, PublicArticle, PublicBookNote, PublicProject, TaxonomyItem } from '~/types/api'
import { apiErrorDetail, isOptimisticLockConflict } from '~/utils/api-errors'
import { AutosaveQueue, type AutosaveState } from '~/utils/autosave'
import { missingImageAltLocation } from '~/utils/markdown-media'

const props = defineProps<{ article: Article }>()
const emit = defineEmits<{ saved: [article: Article] }>()
const workspace = ref<InstanceType<typeof WritingWorkspace> | null>(null)
const publication = ref<InstanceType<typeof StudioPublishConfirmation> | null>(null)
const current = ref({ ...props.article })
const form = reactive({
  title: props.article.title,
  slug: props.article.slug,
  summary: props.article.summary,
  content: props.article.content,
  category_id: props.article.category?.id ?? null,
  tag_ids: props.article.tags.map(tag => tag.id),
  references: (props.article.references || []).map(item => ({ ...item })),
})
const saveState = ref<AutosaveState>('idle')
const publishing = ref(false)
const publishError = ref('')
const { data: categories, error: categoriesError } = await useAsyncData('admin-categories', () =>
  apiFetch<TaxonomyItem[]>('/admin/categories'),
)
const { data: tags, error: tagsError } = await useAsyncData('admin-tags', () =>
  apiFetch<TaxonomyItem[]>('/admin/tags'),
)
const { data: publishedArticles, error: publishedArticlesError } = await useAsyncData('reference-articles', () =>
  apiFetch<PublicArticle[]>('/articles?limit=100&offset=0'),
)
const { data: publishedProjects, error: publishedProjectsError } = await useAsyncData('reference-projects', () =>
  apiFetch<PublicProject[]>('/projects?limit=100&offset=0'),
)
const { data: publishedBooks, error: publishedBooksError } = await useAsyncData('reference-books', () =>
  apiFetch<PublicBookNote[]>('/books?limit=100&offset=0'),
)
useApiFailure(categoriesError)
useApiFailure(tagsError)
useApiFailure(publishedArticlesError)
useApiFailure(publishedProjectsError)
useApiFailure(publishedBooksError)

type PickerTarget = { type: ContentType, id: number, title: string }
const pickerTargets = computed<PickerTarget[]>(() => [
  ...(publishedArticles.value || [])
    .filter(item => item.id !== current.value.id)
    .map(item => ({ type: 'article' as const, id: item.id, title: item.title })),
  ...(publishedProjects.value || []).map(item => ({ type: 'project' as const, id: item.id, title: item.title })),
  ...(publishedBooks.value || []).map(item => ({ type: 'book' as const, id: item.id, title: item.book_title })),
])
const targetsFor = (type: ContentType | null) => pickerTargets.value.filter(item => item.type === (type || 'article'))
const addReference = () => {
  if (form.references.length >= 20) return
  form.references.push({
    kind: 'internal',
    display_title: '',
    url: null,
    target_type: 'article',
    target_id: null,
  })
}
const assignInternalTarget = (item: ArticleReference, rawId: string) => {
  const id = Number(rawId)
  const target = targetsFor(item.target_type).find(entry => entry.id === id)
  item.target_id = target?.id ?? null
  if (target && !item.display_title.trim()) item.display_title = target.title
}

const isCompleteReference = (item: ArticleReference) => {
  if (!item.display_title.trim()) return false
  if (item.kind === 'external') return Boolean(item.url)
  return item.target_id != null
}
const incompleteReferenceIndex = computed(() => form.references.findIndex(item => !isCompleteReference(item)))
const checkReferences = async () => {
  if (incompleteReferenceIndex.value < 0) return true
  publishError.value = '参考资料尚未填完，请补齐或移除。其他完整内容按自动保存状态为准。'
  await workspace.value?.reveal(`[data-testid="reference-title-${incompleteReferenceIndex.value}"]`)
  return false
}
onBeforeRouteLeave(checkReferences)
const protectReferences = (event: BeforeUnloadEvent) => {
  if (incompleteReferenceIndex.value < 0) return
  event.preventDefault()
  event.returnValue = ''
}
onMounted(() => window.addEventListener('beforeunload', protectReferences))
onBeforeUnmount(() => window.removeEventListener('beforeunload', protectReferences))
const save = async (snapshot: typeof form) => {
  if (!await workspace.value?.validate(false)) throw new Error('请检查必填字段与内容设置。')
  const updated = await apiFetch<Article>('/admin/articles/' + current.value.id, {
    method: 'PATCH',
    body: {
      ...snapshot,
      references: snapshot.references.filter(isCompleteReference),
      version: current.value.version,
    },
  })
  current.value = updated
  emit('saved', updated)
}

const queue = new AutosaveQueue(
  save,
  state => {
    saveState.value = state
  },
)
const { flushBeforeNavigation: flushBeforeAction } = useAutosaveSafety(queue, () => { void workspace.value?.focusInvalid() })

watch(
  form,
  value => queue.schedule({
    ...value,
    tag_ids: [...value.tag_ids],
    references: value.references.map(item => ({ ...item })),
  }),
  { deep: true },
)

const retrySave = async () => {
  if (await workspace.value?.validate()) await flushBeforeAction()
}
const stateLabel = computed(() => ({
  idle: '尚未修改',
  pending: '等待保存',
  saving: '保存中…',
  saved: '已自动保存',
  error: '保存失败',
  conflict: '内容冲突',
})[saveState.value])

const publish = async () => {
  if (publishing.value) return
  const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null
  publishing.value = true
  try {
    publishError.value = ''
    if (!await checkReferences()) return
    if (!await workspace.value?.validate()) return
    const missingAlt = missingImageAltLocation(form.content)
    if (missingAlt) {
      publishError.value = `第 ${missingAlt.line} 行、第 ${missingAlt.column} 列的图片缺少 Alt 文本，补齐后才能发布。`
      await workspace.value?.reveal('[data-testid="content"]')
      return
    }
    if (!await flushBeforeAction()) return
    if (!await publication.value?.request(current.value.status === 'published')) {
      publishing.value = false
      await nextTick()
      trigger?.focus()
      return
    }
    const updated = await apiFetch<Article>('/admin/articles/' + current.value.id + '/publish', {
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
  finally {
    publishing.value = false
  }
}

</script>
