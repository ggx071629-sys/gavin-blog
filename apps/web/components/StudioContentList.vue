<template>
  <section class="writing-page studio-content-list" :aria-labelledby="`${kind}-title`">
    <header class="admin-page-header">
      <div><h1 :id="`${kind}-title`" class="admin-page-title">{{ heading }}</h1><p class="admin-page-description">{{ description }}</p></div>
      <NuxtLink class="button-primary" :to="`${path}/new`"><StudioIcon name="plus" />{{ createLabel }}</NuxtLink>
    </header>
    <nav class="list-filters" aria-label="发布状态筛选">
      <NuxtLink v-for="filter in filters" :key="filter.value" :to="{ path, query: { q: query.q || undefined, status: filter.value || undefined } }" :aria-current="query.status === filter.value ? 'page' : undefined">
        {{ filter.label }} <span v-if="result && !error && !pending">{{ result.counts[filter.key] }}</span>
      </NuxtLink>
    </nav>
    <aside v-if="unpublished.length && !pending && !error" class="list-attention">
      <StudioIcon name="alert-circle-filled" />
      <div><strong>本页 {{ unpublished.length }} 项有未发布修改</strong><p>草稿已保存，访客看到的仍是上次发布的版本。</p><NuxtLink :to="`${path}/${unpublished[0]!.id}/edit`">继续编辑</NuxtLink></div>
    </aside>
    <div class="list-summary">
      <h2>{{ kind === 'books' ? '书架与笔记' : '最近更新' }}</h2>
      <form class="list-search" role="search" @submit.prevent="search">
        <label class="sr-only" :for="`${kind}-search`">{{ searchLabel }}</label>
        <input :id="`${kind}-search`" v-model="term" type="search" maxlength="200" :placeholder="searchLabel">
        <button type="submit" class="button-secondary" aria-label="搜索"><StudioIcon name="search" /></button>
      </form>
    </div>
    <div v-if="pending" role="status" class="list-message">正在读取内容…</div>
    <div v-else-if="error" role="alert" class="list-message">
      <h2>列表读取失败</h2><p>搜索条件已保留，请重试。</p><button type="button" class="button-secondary" @click="refresh()">重新读取</button>
    </div>
    <template v-else>
      <p v-if="actionError && !selected" role="alert" class="admin-feedback admin-feedback-error">{{ actionError }}</p>
      <div v-if="items.length" class="list-table">
        <div class="list-head" aria-hidden="true"><span>{{ kind === 'books' ? '书籍 / 作者' : kind === 'projects' ? '标题 / 技术信息' : '标题 / 栏目' }}</span><span>发布状态</span><span>更新于</span><span>操作</span></div>
        <article v-for="item in items" :key="item.id" class="content-row">
          <div class="list-copy">
            <h2><NuxtLink :to="`${path}/${item.id}/edit`">{{ titleOf(item) }}</NuxtLink></h2>
            <p class="list-meta"><span>{{ subtitleOf(item) }}</span><span>/{{ item.slug }}</span></p>
            <p class="list-meta"><span v-if="'reading_status' in item">{{ readingStatusLabel(item.reading_status) }}</span><span>版本 v{{ item.version }}</span><span v-if="item.current_publish_revision" data-testid="article-revision">发布 #{{ item.current_publish_revision }}</span></p>
          <p v-if="'repository_url' in item" class="list-project-links">
            <a v-if="item.repository_url" :href="item.repository_url" target="_blank" rel="noopener noreferrer">仓库 <StudioIcon name="external-link" /></a>
            <a v-if="item.website_url" :href="item.website_url" target="_blank" rel="noopener noreferrer">站点 <StudioIcon name="external-link" /></a>
          </p>
          </div>
          <div class="list-status"><span class="status-chip admin-status" :data-status="item.status">{{ item.status === 'published' ? '已发布' : '草稿' }}</span><span v-if="item.status === 'published' && item.has_unpublished_changes" class="admin-attention-badge">有未发布修改</span></div>
          <time class="writing-list-date" :datetime="item.updated_at">{{ new Date(item.updated_at).toLocaleDateString('zh-CN') }}</time>
          <div class="list-actions">
            <NuxtLink :to="`${path}/${item.id}/edit`" class="list-edit">编辑</NuxtLink>
            <button type="button" class="list-more" :aria-label="`${titleOf(item)}的更多操作`" @click="selected = item"><StudioIcon name="dots" />更多</button>
          </div>
        </article>
      </div>
      <div v-else class="list-message">
        <h2>{{ query.q || query.status || page > 1 ? '没有匹配的内容' : `还没有${heading}` }}</h2>
        <p>{{ query.q || query.status || page > 1 ? '换一个关键词，或回到全部内容。' : '从一篇草稿开始，保存后再决定何时发布。' }}</p>
        <NuxtLink v-if="query.q || query.status || page > 1" class="button-secondary" :to="path">清除搜索与筛选</NuxtLink>
        <NuxtLink v-else class="button-secondary" :to="`${path}/new`">{{ createLabel }}</NuxtLink>
      </div>
      <footer class="list-pagination"><p v-if="result">共 {{ result.total }} 项 · 每页 {{ pageSize }} 项</p><PaginationNav :page="page" :has-next="hasNext" :path="path" :query="query" /></footer>
    </template>
    <AdminDialog :model-value="!!selected" labelledby="list-dialog-title" :close-disabled="deleting" @update:model-value="selected = null">
      <div v-if="selected" class="list-dialog-actions">
        <h2 id="list-dialog-title">{{ titleOf(selected) }}</h2>
        <button type="button" class="button-secondary" :disabled="deleting" @click="selected = null">关闭</button>
        <NuxtLink v-if="kind === 'articles'" class="button-secondary" :to="`${path}/${selected.id}/preview`">预览草稿</NuxtLink>
        <NuxtLink v-if="kind === 'articles'" class="button-secondary" :to="`${path}/${selected.id}/revisions`">版本历史</NuxtLink>
        <NuxtLink v-if="selected.public_path" class="button-secondary" :to="selected.public_path">查看已发布版本</NuxtLink>
        <p>移入回收站后，可在「回收站与迁移」中恢复。</p>
        <button type="button" class="admin-danger-button" :disabled="deleting" @click="trash">{{ deleting ? '正在移入回收站…' : '移入回收站' }}</button>
        <p v-if="actionError" role="alert">{{ actionError }}</p>
      </div>
    </AdminDialog>
  </section>
</template>
<script setup lang="ts">
import type { AdminListQuery, Article, BookNote, Project } from '~/types/api'
import { paginatedApiPath } from '~/utils/pagination'
import { readingStatusLabel } from '~/utils/content'
type Item = Article | BookNote | Project
const props = defineProps<{ kind: 'articles' | 'books' | 'projects'; heading: string; description: string; createLabel: string }>()
const route = useRoute()
const path = `/admin/${props.kind}`
const pageSize = 20
const page = useBoundedPage(pageSize)
const query = computed(() => ({ q: typeof route.query.q === 'string' ? route.query.q.trim().slice(0, 200) : '', status: route.query.status === 'draft' || route.query.status === 'published' ? route.query.status : '' }))
const term = ref(query.value.q)
watch(() => query.value.q, value => { term.value = value })
const searchLabel = computed(() => props.kind === 'books' ? '搜索书名或作者' : '搜索标题')
const search = () => navigateTo({ path, query: { q: term.value.trim() || undefined, status: query.value.status || undefined } })
const endpoint = computed(() => paginatedApiPath(`${path}/query`, page.value, pageSize, query.value))
const { data: result, error, pending, refresh } = await useAsyncData(`studio-${props.kind}-query`, () => apiFetch<AdminListQuery<Item>>(endpoint.value), { watch: [endpoint] })
const items = computed(() => result.value?.items.slice(0, pageSize) || [])
const hasNext = computed(() => (result.value?.total || 0) > page.value * pageSize)
const unpublished = computed(() => items.value.filter(item => item.status === 'published' && item.has_unpublished_changes))
const filters = [{ label: '全部', value: '', key: 'all' }, { label: '已发布', value: 'published', key: 'published' }, { label: '草稿', value: 'draft', key: 'draft' }] as const
const titleOf = (item: Item) => 'book_title' in item ? item.book_title : item.title
const subtitleOf = (item: Item) => 'book_title' in item ? item.author : 'category' in item ? item.category?.name || '未分类' : item.summary
const selected = ref<Item | null>(null)
const deleting = ref(false)
const actionError = ref('')
const trash = async () => {
  if (!selected.value || deleting.value || !confirm(`将“${titleOf(selected.value)}”移入回收站？`)) return
  deleting.value = true
  actionError.value = ''
  try {
    await apiFetch(`${path}/${selected.value.id}`, { method: 'DELETE' })
    selected.value = null
    await refresh()
    if (!error.value && !items.value.length && page.value > 1) await navigateTo({ path, query: { ...query.value, page: String(page.value - 1) } })
  }
  catch { actionError.value = '删除失败，内容仍保留，请重试。' }
  finally { deleting.value = false }
}
</script>
<style scoped>
.studio-content-list .admin-page-title { font-size: 36px; }
.list-filters { display: flex; gap: 18px; border-bottom: 1px solid var(--ee-line-soft); }
.list-filters a { padding: 0 16px; font-size: 18px; min-height: 54px; display: flex; align-items: center; gap: 10px; border-bottom: 2px solid transparent; color: var(--ee-ink-muted); }
.list-filters a[aria-current] { color: var(--ee-primary); border-bottom-color: var(--ee-primary); }
.list-filters span { font-size: 13px; font-variant-numeric: tabular-nums; }
.list-attention { display: flex; gap: 22px; margin: 32px 0; padding: 12px 28px; border-left: 4px solid var(--ee-warning-border); }
.list-attention strong { font-size: 20px; }
.list-attention + .list-summary { border-top: 1px solid var(--ee-line-soft); padding-top: 32px; }
.list-attention > .studio-icon { color: var(--ee-warning-ink); flex-shrink: 0; }
.list-attention p { color: var(--ee-ink-muted); margin: 6px 0; }
.list-attention a { color: var(--ee-primary); display: inline-flex; align-items: center; min-height: 44px; }
.list-summary { display: flex; justify-content: space-between; align-items: center; gap: 20px; padding: 28px 0 20px; }
.list-summary h2 { font-size: 20px; font-weight: 600; }
.list-search { display: flex; gap: 8px; max-width: 100%; }
.list-search input { width: 260px; min-width: 0; border: 1px solid var(--ee-line); border-radius: 7px; background: var(--ee-canvas); padding: 10px 14px; font-size: 16px; }
.list-head, .content-row { display: grid; grid-template-columns: minmax(0, 1fr) 130px 105px 120px; gap: 20px; align-items: center; }
.list-head { color: var(--ee-ink-muted); font-size: 13px; padding: 12px 0; border-bottom: 1px solid var(--ee-line-soft); }
.list-head > :last-child { text-align: right; }
.content-row { padding: 24px 0; border-bottom: 1px solid var(--ee-line-soft); }
.list-copy { min-width: 0; overflow-wrap: anywhere; }
.list-copy h2 { font-size: 18px; font-weight: 600; line-height: 1.6; }
.list-copy h2 a:hover { color: var(--ee-primary); }
.list-meta { display: flex; flex-wrap: wrap; gap: 6px 14px; font-size: 13px; color: var(--ee-ink-muted); margin-top: 6px; }
.list-project-links { display: flex; flex-wrap: wrap; gap: 16px; font-size: 13px; color: var(--ee-primary); }
.list-project-links a { min-height: 44px; display: inline-flex; gap: 5px; align-items: center; }
.list-project-links .studio-icon { width: 14px; height: 14px; }
.list-status { display: flex; flex-wrap: wrap; gap: 8px; align-items: start; }
.list-actions { display: flex; justify-content: end; gap: 12px; }
.list-edit, .list-more { min-height: 44px; display: inline-flex; align-items: center; gap: 4px; color: var(--ee-primary); }
.list-more { color: var(--ee-ink-muted); }
.list-more .studio-icon { width: 16px; }
.list-message { padding: 48px 0; display: grid; justify-items: start; gap: 14px; }
.list-message h2 { font-size: 20px; }
.list-message p, .list-pagination { color: var(--ee-ink-muted); }
.list-pagination { padding: 24px 0; display: flex; gap: 20px; align-items: center; justify-content: space-between; flex-wrap: wrap; font-size: 13px; }
.list-pagination :deep(nav) { margin: 0; padding: 0; border: 0; }
.list-dialog-actions { display: grid; gap: 16px; }
@media (max-width: 1200px) {
  .list-head, .content-row { grid-template-columns: minmax(0, 1fr) 105px 105px; gap: 16px; }
  .content-row .writing-list-date { grid-column: 1; grid-row: 2; }
  .list-head > :nth-child(3) { display: none; }
}
@media (max-width: 760px) {
  .studio-content-list .admin-page-title { font-size: 30px; }
  .list-summary { flex-direction: column; align-items: stretch; }
  .list-search input { width: 100%; }
  .list-search button { flex-shrink: 0; }
  .list-head { display: none; }
  .content-row { grid-template-columns: minmax(0, 1fr) auto; gap: 12px; }
  .list-copy, .list-status { grid-column: 1 / -1; }
  .content-row .writing-list-date { grid-column: 1; grid-row: auto; }
  .list-actions { grid-column: 2; }
  .list-filters { gap: 10px; }
  .list-filters a { padding: 0 8px; font-size: 16px; }
  .list-attention { gap: 12px; padding: 8px 14px; }
}
</style>
