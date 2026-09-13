<template>
  <section class="resource-ops studio-about-history space-y-6">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">关于页版本历史</h1>
        <p v-if="page" class="mt-1 text-sm text-ee-ink-faint">
          当前发布修订：{{ page.current_publish_revision ?? '—' }}
          <template v-if="page.has_unpublished_changes"> · 有未发布修改</template>
        </p>
      </div>
      <NuxtLink class="button-secondary" to="/admin/about">返回编辑器</NuxtLink>
    </header>

    <div v-if="error" role="alert" class="rounded-ee-soft border border-ee-danger-border bg-ee-danger-bg p-4 text-sm text-ee-danger-ink">{{ error }}</div>
    <div v-if="message" role="status" class="rounded-ee-soft border border-ee-success-border bg-ee-success-bg p-4 text-sm text-ee-success-ink">{{ message }}</div>

    <p v-if="loading || acting" role="status">正在读取或处理版本…</p>
    <button v-if="error" type="button" class="button-secondary" @click="reloadHistory">重新读取历史</button>
    <div class="grid gap-6 lg:grid-cols-2" :aria-busy="loading || acting">
      <section class="ops-panel" aria-labelledby="revision-list-title" data-testid="about-revision-list">
        <h2 id="revision-list-title">发布修订</h2>
        <ul class="mt-4 space-y-3">
          <li
            v-for="revision in revisions"
            :key="revision.id"
            class="rounded-ee-soft border border-ee-line bg-ee-surface-low p-4 dark:border-ee-line dark:bg-ee-surface-low"
            :class="{ 'is-selected': revision.id === selectedId }"
          >
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div class="flex flex-wrap items-center gap-2">
                <span class="font-semibold">修订 {{ revision.revision_number }}</span>
                <span class="status-chip admin-status">{{ SOURCE_LABELS[revision.source] || revision.source }}</span>
                <span v-if="revision.id === page?.current_revision_id" class="status-chip admin-status" data-testid="about-current-revision">当前发布</span>
              </div>
              <span class="text-sm text-ee-ink-faint">{{ formatDate(revision.published_at) }}</span>
            </div>
            <div class="mt-3 flex flex-wrap gap-2">
              <button type="button" class="button-secondary" data-testid="about-revision-view" :disabled="acting" @click="view(revision)">查看快照</button>
              <button type="button" class="button-secondary" data-testid="about-revision-compare" :disabled="acting || !page?.current_revision_id" @click="compare(revision)">与当前比较</button>
              <button
                v-if="canRollback(revision)"
                type="button"
                class="button-secondary"
                data-testid="about-revision-rollback"
                :disabled="acting"
                @click="rollbackTarget = revision"
              >回滚到此版本</button>
            </div>
          </li>
        </ul>
        <button v-if="revisions.length < total" class="button-secondary mt-4" type="button" :disabled="loading || acting" @click="loadMore">{{ loading ? '加载中…' : '加载更多版本' }}</button>
        <p v-if="!revisions.length && !error && !loading" class="mt-4 text-sm text-ee-ink-faint">暂无发布修订。</p>
      </section>

      <aside ref="readingPanel" class="space-y-5" tabindex="-1">
        <p v-if="!detail && !diff && !acting" class="history-hint">选择发布记录，查看快照或与当前版本比较。</p>
        <section v-if="detail" class="ops-panel" data-testid="about-revision-detail">
          <div class="flex items-center justify-between gap-3">
            <h2 class="text-sm font-semibold">修订 #{{ detail.revision_number }} 快照</h2>
            <button type="button" class="button-secondary" @click="detail = null; showPreview = false">关闭</button>
          </div>
          <p class="mt-2 text-sm text-ee-ink-faint">
            {{ formatDate(detail.published_at) }} · {{ SOURCE_LABELS[detail.source] || detail.source }} · {{ detail.content_sha256.slice(0, 16) }}…
          </p>
          <p class="mt-4" data-testid="about-snapshot-statement">{{ detail.content.statement }}</p>
          <button type="button" class="button-secondary mt-3" data-testid="about-revision-preview-toggle" @click="showPreview = !showPreview">
            {{ showPreview ? '隐藏整页预览' : '显示整页预览' }}
          </button>
        </section>

        <section v-if="diff" class="ops-panel" data-testid="about-revision-diff-panel">
          <h2 class="text-sm font-semibold">差异：{{ diff.from_revision_id }} → {{ diff.to_revision_id }}</h2>
          <div class="mt-3 space-y-3 text-sm">
            <div v-for="(value, field) in diffFields" :key="field">
              <h3 v-if="value" class="mb-1 font-semibold">{{ FIELD_LABELS[field as keyof typeof FIELD_LABELS] }}</h3>
              <pre v-if="value" class="admin-code-panel max-h-52 overflow-auto whitespace-pre-wrap">{{ value }}</pre>
            </div>
          </div>
        </section>
      </aside>
    </div>

    <div v-if="showPreview && detail" class="blueprint-wrapper">
      <AboutPublicBody :content="detail.content" :profile="profile ?? null" />
    </div>

    <AdminDialog
      :model-value="Boolean(rollbackTarget)"
      labelledby="about-rollback-title"
      test-id="about-rollback-modal"
      :close-disabled="acting"
      @update:model-value="rollbackTarget = null"
    >
      <template v-if="rollbackTarget">
        <h2 id="about-rollback-title" class="text-lg font-semibold">确认回滚</h2>
        <p class="mt-3 text-sm text-ee-ink-muted">
          将关于页回滚到修订 #{{ rollbackTarget.revision_number }}。回滚会创建新的不可变修订，不会改写历史；存在未发布工作副本时会被拒绝。
        </p>
        <div class="mt-5 flex justify-end gap-2">
          <button type="button" class="button-secondary" :disabled="acting" @click="rollbackTarget = null">取消</button>
          <button type="button" class="button-primary" data-testid="about-rollback-confirm" :disabled="acting" @click="rollback">
            {{ acting ? '回滚中…' : '确认回滚' }}
          </button>
        </div>
      </template>
    </AdminDialog>
  </section>
</template>

<script setup lang="ts">
import type {
  AboutPageAdmin,
  AboutRevisionDetail,
  AboutRevisionDiffResponse,
  AboutRevisionSummary,
  ProfilePublic,
} from '~/types/api'

definePageMeta({ layout: 'admin-core', middleware: 'admin' })
useSeoMeta({ title: '关于页版本历史' })

const page = ref<AboutPageAdmin | null>(null)
const revisions = ref<AboutRevisionSummary[]>([])
const detail = ref<AboutRevisionDetail | null>(null)
const diff = ref<AboutRevisionDiffResponse | null>(null)
const rollbackTarget = ref<AboutRevisionSummary | null>(null)
const showPreview = ref(false)
const acting = ref(false)
const loading = ref(false)
const total = ref(0)
const selectedId = ref<number | null>(null)
const readingPanel = ref<HTMLElement | null>(null)
const revealReading = async () => {
  await nextTick()
  if (window.innerWidth <= 900) { readingPanel.value?.scrollIntoView({ block: 'start' }); readingPanel.value?.focus({ preventScroll: true }) }
}
const error = ref('')
const message = ref('')

const SOURCE_LABELS: Record<string, string> = {
  editor: '编辑器发布',
  rollback: '版本回滚',
}
const FIELD_LABELS = {
  statement: '引言',
  capabilities: '能力领域',
  now: '最近在做',
  editorial_topics: '写作范围',
  site: '网站说明',
}
const diffFields = computed(() => diff.value ? Object.fromEntries(
  Object.entries(diff.value).filter(([key]) => key in FIELD_LABELS),
) : {})

const { data: profile, error: profileError } = await useAsyncData<ProfilePublic>(
  'about-revision-profile',
  () => apiFetch<ProfilePublic>('/profile'),
)
useApiFailure(profileError)

const formatDate = (value: string) =>
  new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))

const canRollback = (revision: AboutRevisionSummary) =>
  page.value?.current_revision_id != null && revision.id !== page.value.current_revision_id

const load = async () => {
  const [about, list] = await Promise.all([
    apiFetch<AboutPageAdmin>('/admin/about-page'),
    apiFetch<{ total: number, revisions: AboutRevisionSummary[] }>('/admin/about-page/revisions'),
  ])
  page.value = about
  revisions.value = list.revisions
  total.value = list.total
}

const reloadHistory = async () => {
  if (loading.value || acting.value) return
  loading.value = true
  error.value = ''
  try { await load() }
  catch (loadError) { error.value = apiErrorDetail(loadError) || '版本历史加载失败' }
  finally { loading.value = false }
}
const loadMore = async () => {
  if (loading.value || acting.value) return
  loading.value = true
  error.value = ''
  try {
    const list = await apiFetch<{ total: number, revisions: AboutRevisionSummary[] }>(`/admin/about-page/revisions?limit=20&offset=${revisions.value.length}`)
    revisions.value = [...revisions.value, ...list.revisions]
    total.value = list.total
  }
  catch (loadError) { error.value = apiErrorDetail(loadError) || '更多版本加载失败' }
  finally { loading.value = false }
}
await reloadHistory()

const view = async (revision: AboutRevisionSummary) => {
  if (acting.value || loading.value) return
  acting.value = true
  error.value = ''
  detail.value = null
  showPreview.value = false
  selectedId.value = revision.id
  diff.value = null
  try {
    detail.value = await apiFetch<AboutRevisionDetail>(`/admin/about-page/revisions/${revision.id}`)
    showPreview.value = true
    await revealReading()
  }
  catch (viewError) {
    error.value = apiErrorDetail(viewError) || '修订快照加载失败'
  }
  finally {
    acting.value = false
  }
}

const compare = async (revision: AboutRevisionSummary) => {
  if (!page.value?.current_revision_id || acting.value || loading.value) return
  error.value = ''
  selectedId.value = revision.id
  diff.value = null
  acting.value = true
  detail.value = null
  showPreview.value = false
  try {
    diff.value = await apiFetch<AboutRevisionDiffResponse>(
      `/admin/about-page/revision-diff?from_revision_id=${revision.id}&to_revision_id=${page.value.current_revision_id}`,
    )
    await revealReading()
  }
  catch (compareError) {
    error.value = apiErrorDetail(compareError) || '差异加载失败'
  }
  finally {
    acting.value = false
  }
}

const rollback = async () => {
  if (!page.value || !rollbackTarget.value || acting.value) return
  acting.value = true
  message.value = ''
  error.value = ''
  try {
    const updated = await apiFetch<AboutPageAdmin>(
      `/admin/about-page/revisions/${rollbackTarget.value.id}/rollback`,
      {
        method: 'POST',
        body: {
          version: page.value.version,
          current_revision_id: page.value.current_revision_id,
          rollback_confirmed: true,
        },
      },
    )
    page.value = updated
    await load()
    rollbackTarget.value = null
    detail.value = null
    diff.value = null
    message.value = `已创建回滚修订 #${updated.current_publish_revision}。`
  }
  catch (rollbackError) {
    error.value = apiErrorDetail(rollbackError) || '回滚失败，请稍后重试。'
  }
  finally {
    acting.value = false
  }
}
</script>

<style scoped>
.studio-about-history { max-width: none; margin: 0; --ee-ink-faint: var(--studio-muted); }
.studio-about-history h1 { font-size: 36px; margin: 0; }
.studio-about-history .ops-panel { border: 0; border-radius: 0; padding: 24px 0; background: none; border-top: 1px solid var(--studio-divider); }
.studio-about-history li { border: 0; border-radius: 0; background: none; border-bottom: 1px solid var(--studio-divider); padding: 20px 12px; }
.studio-about-history li.is-selected { background: var(--studio-selected); }
.studio-about-history aside { min-width: 0; scroll-margin-top: 24px; }
.studio-about-history pre { white-space: pre-wrap; overflow-wrap: anywhere; }
.history-hint { color: var(--studio-muted); border-top: 1px solid var(--studio-divider); padding-top: 24px; }
.studio-about-history .blueprint-wrapper { overflow-wrap: anywhere; min-width: 0; }
.studio-about-history :deep(.about-editorial) { padding-inline: 0; }
@media (max-width: 760px) { .studio-about-history h1 { font-size: 28px; } }
</style>
