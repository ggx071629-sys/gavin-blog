<template>
  <section class="resource-ops resource-ops--content space-y-6">
    <div>
      <h1 class="mt-3 text-3xl font-semibold">回收站与迁移</h1>
      <p class="mt-3 text-sm text-ee-ink-faint">恢复误删内容，或以可读 Markdown 格式备份和迁移。</p>
    </div>

    <section class="studio-trash" aria-labelledby="trash-title">
      <div class="flex items-center justify-between"><h2 id="trash-title" class="text-lg font-semibold">回收站</h2><span class="text-sm text-ee-ink-faint">本页 {{ trash.length }} 项</span></div>
      <p v-if="trashError" class="mt-3 text-sm text-ee-danger-ink" role="alert" data-testid="trash-error">{{ trashError }}</p>
      <div v-if="trash.length" class="studio-trash-list mt-4">
        <article v-for="item in trash" :key="`${item.content_type}-${item.content_id}`" class="ops-trash-row last:border-0">
          <div><div class="flex items-center gap-2"><span class="status-chip">{{ typeLabel[item.content_type] }}</span><span class="text-sm text-ee-ink-faint">{{ formatDate(item.deleted_at) }}</span></div><h3 class="mt-2 font-semibold">{{ item.title }}</h3><p class="mt-1 text-sm text-ee-ink-faint">{{ item.slug }}</p></div>
          <div class="flex flex-wrap gap-3"><button class="button-secondary" type="button" :disabled="trashBusy" @click="restore(item)">恢复</button><button class="button-secondary text-ee-danger-ink hover:bg-ee-danger-bg" type="button" :disabled="trashBusy" @click="purge(item)">永久删除</button></div>
        </article>
      </div>
      <div v-else class="empty-state mt-4">回收站为空。</div>
      <PaginationNav :page="page" :has-next="hasNext" path="/admin/content" />
    </section>
    <div class="ops-transfer" aria-label="Markdown 迁移">
      <section class="ops-panel">
        <h2>导入 Markdown</h2>
        <p>选择文件创建草稿，检查内容后再到编辑器发布。</p>
        <label class="field mt-4">
          <span>选择 Markdown 文件（最多 50 个）</span>
          <input data-testid="import-markdown" type="file" accept=".md,text/markdown" multiple :disabled="importing" @change="importMarkdown">
        </label>
        <div class="mt-3 text-sm" aria-live="polite" :class="messageIsError ? 'text-ee-danger-ink' : 'text-ee-success-ink'">{{ importing ? '正在导入…' : message }}</div>
        <ul v-if="imported.length" class="mt-3 space-y-3 text-sm">
          <li v-for="item in imported" :key="`${item.content_type}-${item.content_id}`">
            <NuxtLink class="admin-inline-action" :to="editPath(item)">{{ item.filename }} <NavigationArrow /> 编辑草稿</NuxtLink>
            <p v-if="item.warnings.length">{{ item.warnings.join('；') }}</p>
          </li>
        </ul>
      </section>
      <section class="ops-panel">
        <h2>导出 Markdown</h2>
        <p>下载可读 Markdown ZIP，用于内容备份与迁移。</p>
        <button class="button-secondary mt-4" data-testid="export-markdown" type="button" :disabled="exporting" @click="exportMarkdown">{{ exporting ? '正在导出…' : '导出 Markdown ZIP' }}</button>
        <div class="mt-3 text-sm" aria-live="polite" :class="exportError ? 'text-ee-danger-ink' : 'text-ee-success-ink'">{{ exportMessage }}</div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import '~/assets/css/resource-operations.css'
import type { ContentType, MarkdownImportItem, MarkdownImportResponse, TrashItem } from '~/types/api'
import { apiErrorDetail } from '~/utils/api-errors'
import { paginatedApiPath, paginationWindow } from '~/utils/pagination'

definePageMeta({ layout: 'admin-core', middleware: 'admin' })
const pageSize = 20
const page = useBoundedPage(pageSize)
const endpoint = computed(() => paginatedApiPath('/admin/trash', page.value, pageSize))
const { data: trashRows, refresh, error } = await useAsyncData('admin-trash', () => apiFetch<TrashItem[]>(endpoint.value), { watch: [endpoint] })
useApiFailure(error)
const window = computed(() => paginationWindow(trashRows.value, pageSize))
const trash = computed(() => window.value.items)
const hasNext = computed(() => window.value.hasNext)
const imported = ref<MarkdownImportItem[]>([])
const message = ref('')
const messageIsError = ref(false)
const trashError = ref('')
const trashBusy = ref(false)
const importing = ref(false)
const exporting = ref(false)
const exportMessage = ref('')
const exportError = ref(false)
const editPath = (item: MarkdownImportItem) => `/admin/${{ article: 'articles', project: 'projects', book: 'books' }[item.content_type]}/${item.content_id}/edit`
const typeLabel: Record<ContentType, string> = { article: '文章', project: '项目', book: '读书' }
const formatDate = (value: string) => new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
const restore = async (item: TrashItem) => {
  if (trashBusy.value) return
  trashBusy.value = true
  trashError.value = ''
  try {
    await apiFetch(`/admin/trash/${item.content_type}/${item.content_id}/restore`, { method: 'POST' })
    await refresh()
  }
  catch (error) {
    trashError.value = apiErrorDetail(error) || '恢复失败，请稍后重试。'
  }
  finally { trashBusy.value = false }
}
const purge = async (item: TrashItem) => {
  if (!confirm(`永久删除“${item.title}”？此操作无法恢复。`)) return
  if (trashBusy.value) return
  trashBusy.value = true
  trashError.value = ''
  try {
    await apiFetch(`/admin/trash/${item.content_type}/${item.content_id}`, { method: 'DELETE' })
    await refresh()
  }
  catch (error) {
    trashError.value = apiErrorDetail(error) || '永久删除失败，请稍后重试。'
  }
  finally { trashBusy.value = false }
}
const exportMarkdown = async () => {
  if (exporting.value) return
  exporting.value = true
  exportMessage.value = ''
  exportError.value = false
  try {
    const config = useRuntimeConfig()
    const blob = await $fetch<Blob>('/admin/exports/markdown', {
      baseURL: config.public.apiBase, credentials: 'include', responseType: 'blob',
    })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'gavin-markdown.zip'
    anchor.click()
    URL.revokeObjectURL(url)
    exportMessage.value = '已生成 ZIP 并开始下载。'
  }
  catch {
    exportError.value = true
    exportMessage.value = '导出失败，请重试。'
  }
  finally { exporting.value = false }
}
const importMarkdown = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  if (!files.length || importing.value) return
  if (files.length > 50) {
    message.value = '一次最多导入 50 个 Markdown 文件。'
    messageIsError.value = true
    input.value = ''
    return
  }
  importing.value = true
  const body = new FormData()
  files.forEach(file => body.append('files', file))
  message.value = ''
  messageIsError.value = false
  try {
    const result = await apiFetch<MarkdownImportResponse>('/admin/imports/markdown', { method: 'POST', body })
    imported.value = result.imported
    message.value = `已导入 ${result.imported.length} 项草稿。`
  }
  catch {
    imported.value = []
    message.value = '导入失败，请检查 front matter、UTF-8 编码和 slug 冲突。'
    messageIsError.value = true
  }
  finally { importing.value = false; input.value = '' }
}
useSeoMeta({ title: '回收站与迁移' })
</script>

<style scoped>
.resource-ops--content { max-width: none; margin: 0; --ee-ink-faint: var(--studio-muted); }
.resource-ops--content h1 { font-size: 36px; margin: 0; }
.studio-trash { border-top: 1px solid var(--studio-divider); padding-top: 28px; }
.resource-ops--content h2 { font-size: 22px; }
.studio-trash-list { border-block: 1px solid var(--studio-divider); }
.resource-ops--content .ops-trash-row { padding: 24px 0; }
.resource-ops--content .ops-trash-row h3 { font-size: 18px; }
.resource-ops--content .ops-transfer { gap: 36px; border-top: 1px solid var(--studio-divider); padding-top: 28px; }
.resource-ops--content .ops-panel { border: 0; border-radius: 0; padding: 0; background: none; }
.resource-ops--content .ops-panel input[type="file"] { width: 100%; min-width: 0; }
@media (max-width: 1000px) { .resource-ops--content .ops-transfer { grid-template-columns: minmax(0, 1fr); } }
@media (max-width: 760px) { .resource-ops--content h1 { font-size: 28px; } }
</style>
