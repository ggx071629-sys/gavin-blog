<template>
  <section class="writing-page studio-revisions">
    <NuxtLink class="admin-back-link" :to="`/admin/articles/${articleId}/edit`"><NavigationArrow direction="left" /> 返回编辑器</NuxtLink>
    <header class="admin-page-header">
      <div class="min-w-0">
        <p class="admin-page-kicker">内容 / 文章 / 版本历史</p>
        <h1 class="admin-page-title" data-testid="revisions-title">
          版本历史
        </h1>
        <p class="admin-page-description" data-testid="revisions-subtitle">
          {{ article?.title }} · 正式发布记录
        </p>
      </div>
      <NuxtLink class="button-secondary" :to="`/admin/articles/${articleId}/preview`">
        预览工作副本
      </NuxtLink>
    </header>

    <p v-if="article" class="studio-revision-notice" role="status">
      草稿自动保存与正式发布记录分开。<span v-if="article.current_publish_revision">当前公开：发布 #{{ article.current_publish_revision }}。</span><span v-else>尚未发布。</span>历史快照只读。
    </p>
    <p v-if="error" class="admin-feedback admin-feedback-error" role="alert" data-testid="revisions-error">{{ error }}</p>
    <p v-if="message" class="admin-feedback admin-feedback-success" role="status" data-testid="revisions-message">{{ message }}</p>

    <p v-if="loading" role="status">正在读取版本历史…</p>
    <button v-if="error" class="button-secondary" type="button" @click="load">重新读取历史</button>
    <div class="admin-audit-grid" :aria-busy="loading">
      <section class="admin-panel" data-testid="revision-history">
        <h2 class="admin-panel-title">发布修订</h2>
        <ul class="mt-4 space-y-3">
          <li
            v-for="revision in revisions"
            :key="revision.id"
            class="admin-revision-row"
            :class="{ 'admin-revision-row-current': revision.id === article?.current_revision_id, 'studio-revision-selected': revision.id === detail?.id || revision.id === diff?.from_revision_id }"
            :data-testid="`revision-row-${revision.id}`"
          >
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div class="flex flex-wrap items-center gap-2">
                <span class="font-semibold">修订 {{ revision.revision_number }}</span>
                <span class="status-chip admin-status">{{ REVISION_SOURCE_LABELS[revision.source] ?? revision.source }}</span>
                <span
                  v-if="revision.id === article?.current_revision_id"
                  class="status-chip admin-status"
                  data-status="published"
                >
                  当前发布
                </span>
              </div>
              <span class="admin-faint-text text-sm">{{ formatDateTime(revision.published_at) }}</span>
            </div>
            <p class="admin-secondary-text mt-2 text-sm">
              {{ revision.title }}
            </p>
            <p v-if="revision.rollback_from_revision_id" class="admin-faint-text mt-1 text-sm">
              回滚自修订 {{ revisionLabel(revision.rollback_from_revision_id) }}
            </p>
            <div class="mt-2 flex flex-wrap gap-2">
              <button
                class="button-secondary text-sm"
                type="button"
                :data-testid="`compare-to-${revision.id}`"
                @click="compareTo(revision)"
              >
                与当前比较
              </button>
              <button
                v-if="canRollback(revision)"
                class="button-secondary text-sm"
                type="button"
                :data-testid="`rollback-to-${revision.id}`"
                :disabled="acting"
                @click="openRollback(revision)"
              >
                回滚到此版本
              </button>
              <button
                class="button-secondary text-sm"
                type="button"
                :data-testid="`view-revision-${revision.id}`"
                :aria-pressed="detail?.id === revision.id"
                @click="viewRevision(revision)"
              >
                查看快照
              </button>
            </div>
          </li>
        </ul>
        <p v-if="!loading && !error && !revisions.length" class="admin-secondary-text mt-4 text-sm">暂无发布修订。</p>
        <nav class="mt-5 flex items-center gap-3 text-sm" aria-label="修订分页">
          <button class="button-secondary" type="button" :disabled="offset <= 0" @click="changeOffset(offset - 20)">
            上一页
          </button>
          <span class="admin-secondary-text">共 {{ total }} 条</span>
          <button class="button-secondary" type="button" :disabled="offset + 20 >= total" @click="changeOffset(offset + 20)">
            下一页
          </button>
        </nav>
      </section>

      <aside ref="selectionPanel" class="studio-revision-selection space-y-5" tabindex="-1" aria-label="版本读取结果" :aria-busy="selectionLoading">
        <p v-if="selectionLoading" role="status">正在读取所选版本…</p>
        <p v-if="!selectionLoading && !detail && !diff" class="admin-panel admin-secondary-text">选择左侧版本查看真实快照，或与当前发布比较。</p>
        <section v-if="detail" class="admin-panel" data-testid="revision-detail">
          <h2 class="admin-panel-title">修订快照 #{{ detail.revision_number }}</h2>
          <p class="mt-2 text-sm font-semibold">{{ detail.title }}</p>
          <p class="admin-secondary-text mt-1 text-sm">{{ detail.summary }}</p>
          <p class="admin-faint-text mt-2 text-sm">
            来源：{{ REVISION_SOURCE_LABELS[detail.source] }} · 校验值 {{ detail.content_sha256.slice(0, 16) }}…
          </p>
          <div class="admin-code-panel max-h-56">
            <MarkdownArticle :content="detail.content" />
          </div>
        </section>

        <section v-if="diff" class="admin-panel" data-testid="revision-diff-panel">
          <h2 class="admin-panel-title">
            差异：修订 {{ revisionLabel(diff.from_revision_id) }} → {{ revisionLabel(diff.to_revision_id) }}
          </h2>
          <div v-if="diff.title" class="mt-3">
            <h3 class="admin-secondary-text text-sm font-semibold">标题</h3>
            <pre class="mt-1 whitespace-pre-wrap text-sm leading-relaxed">{{ diff.title }}</pre>
          </div>
          <div v-if="diff.summary" class="mt-3">
            <h3 class="admin-secondary-text text-sm font-semibold">摘要</h3>
            <pre class="mt-1 whitespace-pre-wrap text-sm leading-relaxed">{{ diff.summary }}</pre>
          </div>
          <div v-if="diff.content" class="mt-3">
            <h3 class="admin-secondary-text text-sm font-semibold">正文</h3>
            <pre class="admin-code-panel whitespace-pre-wrap" data-testid="revision-diff-body">{{ diff.content }}</pre>
          </div>
          <div v-if="diff.category || diff.tags || diff.references" class="admin-secondary-text mt-3 space-y-1 text-sm">
            <p v-if="diff.category">栏目：{{ diff.category }}</p>
            <p v-if="diff.tags">标签：{{ diff.tags }}</p>
            <p v-if="diff.references">参考资料：{{ diff.references }}</p>
          </div>
        </section>
      </aside>
    </div>

    <AdminDialog :model-value="Boolean(rollbackTarget)" labelledby="rollback-title" test-id="rollback-modal" :close-disabled="acting" @update:model-value="rollbackTarget = null">
      <template v-if="rollbackTarget">
        <h2 id="rollback-title" class="admin-panel-title">确认回滚</h2>
        <p class="admin-secondary-text mt-3 text-sm">
          将当前文章 #{{ articleId }} 回滚到修订 #{{ rollbackTarget.revision_number }}（{{ rollbackTarget.title }}）。
        </p>
        <p class="admin-secondary-text mt-2 text-sm">
          回滚会创建新的不可变修订（来源 rollback），不会改写历史。文章存在未发布工作副本时将拒绝执行。
        </p>
        <div class="mt-5 flex justify-end gap-2">
          <button class="button-secondary" type="button" :disabled="acting" @click="rollbackTarget = null">取消</button>
          <button
            class="button-primary"
            type="button"
            data-testid="confirm-rollback"
            :disabled="acting"
            @click="rollback"
          >
            确认回滚
          </button>
        </div>
      </template>
    </AdminDialog>
  </section>
</template>

<script setup lang="ts">
import type {
  Article,
  ArticleRevisionDetail,
  ArticleRevisionDiffResponse,
  ArticleRevisionSummary,
} from '~/types/api'
import { REVISION_SOURCE_LABELS, revisionErrorLabel } from '~/utils/articleRevisions'

definePageMeta({ layout: 'admin-core', middleware: 'admin' })

const route = useRoute()
const articleId = Number(route.params.id)
const article = ref<Article | null>(null)
const revisions = ref<ArticleRevisionSummary[]>([])
const total = ref(0)
const offset = ref(0)
const selectionPanel = ref<HTMLElement | null>(null)
const selectionLoading = ref(false)
const detail = ref<ArticleRevisionDetail | null>(null)
const diff = ref<ArticleRevisionDiffResponse | null>(null)
const rollbackTarget = ref<ArticleRevisionSummary | null>(null)
const error = ref('')
const message = ref('')
const acting = ref(false)
const loading = ref(false)
let loadGeneration = 0
let selectionGeneration = 0

const formatDateTime = (value: string) =>
  new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))

const canRollback = (revision: ArticleRevisionSummary) =>
  article.value?.current_revision_id != null
  && revision.id !== article.value.current_revision_id

const load = async () => {
  const generation = ++loadGeneration
  loading.value = true
  error.value = ''
  try {
    const [articleData, revisionData] = await Promise.all([
      apiFetch<Article>(`/admin/articles/${articleId}`),
      apiFetch<{ total: number; revisions: ArticleRevisionSummary[] }>(
        `/admin/articles/${articleId}/revisions?limit=20&offset=${offset.value}`,
      ),
    ])
    if (generation !== loadGeneration) return
    article.value = articleData
    revisions.value = revisionData.revisions
    total.value = revisionData.total
  }
  catch (loadError) {
    if (generation !== loadGeneration) return
    const data = (loadError as { response?: { _data?: { error?: { message?: string } } } })
      .response?._data
    error.value = data?.error?.message ?? '修订历史加载失败'
  }
  finally { if (generation === loadGeneration) loading.value = false }
}

const changeOffset = (next: number) => {
  offset.value = Math.max(0, next)
  void load()
}

const revisionLabel = (id: number) => {
  const revision = revisions.value.find(item => item.id === id)
  return revision ? `#${revision.revision_number}` : `ID ${id}`
}
const revealSelection = async () => {
  await nextTick()
  selectionPanel.value?.focus({ preventScroll: true })
  if (window.matchMedia('(max-width: 767px)').matches) selectionPanel.value?.scrollIntoView({ block: 'start' })
}
const viewRevision = async (revision: ArticleRevisionSummary) => {
  const generation = ++selectionGeneration
  selectionLoading.value = true
  detail.value = null; diff.value = null
  error.value = ''
  try {
    const result = await apiFetch<ArticleRevisionDetail>(
      `/admin/articles/${articleId}/revisions/${revision.id}`,
    )
    if (generation === selectionGeneration) { detail.value = result; await revealSelection() }
  }
  catch (viewError) {
    if (generation !== selectionGeneration) return
    const data = (viewError as { response?: { _data?: { error?: { message?: string } } } })
      .response?._data
    error.value = data?.error?.message ?? '修订快照加载失败'
  }
  finally { if (generation === selectionGeneration) selectionLoading.value = false }
}

const compareTo = async (revision: ArticleRevisionSummary) => {
  if (!article.value?.current_revision_id) return
  const generation = ++selectionGeneration
  selectionLoading.value = true
  detail.value = null; diff.value = null
  error.value = ''
  try {
    const result = await apiFetch<ArticleRevisionDiffResponse>(
      `/admin/articles/${articleId}/revision-diff`
      + `?from_revision_id=${revision.id}&to_revision_id=${article.value.current_revision_id}`,
    )
    if (generation === selectionGeneration) { diff.value = result; await revealSelection() }
  }
  catch (diffError) {
    if (generation !== selectionGeneration) return
    const data = (diffError as { response?: { _data?: { error?: { message?: string } } } })
      .response?._data
    error.value = data?.error?.message ?? '差异加载失败'
  }
  finally { if (generation === selectionGeneration) selectionLoading.value = false }
}

const openRollback = (revision: ArticleRevisionSummary) => {
  rollbackTarget.value = revision
  message.value = ''
}

const rollback = async () => {
  if (!rollbackTarget.value || !article.value?.current_revision_id) return
  acting.value = true
  error.value = ''
  message.value = ''
  try {
    await apiFetch(`/admin/articles/${articleId}/revisions/${rollbackTarget.value.id}/rollback`, {
      method: 'POST',
      body: {
        version: article.value.version,
        current_revision_id: article.value.current_revision_id,
        rollback_confirmed: true,
      },
    })
    rollbackTarget.value = null
    selectionGeneration++
    selectionLoading.value = false
    detail.value = null; diff.value = null
    offset.value = 0
    await load()
    message.value = '回滚完成，已创建新的不可变修订。'
  }
  catch (rollbackError) {
    const data = (rollbackError as { response?: { _data?: { error?: { code?: string; message?: string } } } })
      .response?._data
    error.value = data?.error?.message ?? '回滚失败'
    if (data?.error?.code === 'ARTICLE_WORKING_COPY_DIRTY') {
      error.value = `回滚被拒绝：${revisionErrorLabel(data.error.code)}。请先发布或恢复编辑器中未发布修改。`
    }
  }
  finally {
    acting.value = false
  }
}

await load()
useSeoMeta({ title: '文章版本历史' })
</script>
