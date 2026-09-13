<template>
  <section class="admin-media-uploader" :class="{ 'admin-media-uploader--management': management }">
    <p v-if="libraryError" role="alert" class="text-sm text-ee-danger-ink">{{ libraryError }}</p>
    <button v-if="!management" class="button-secondary mt-3" type="button" data-testid="toggle-media-library" @click="toggleLibrary">
      {{ showLibrary ? '收起已有媒体' : '选择已有媒体' }}
    </button>

    <div v-if="showLibrary" class="media-library mt-4 rounded-ee-soft border border-ee-line p-4">
      <h2 v-if="management" class="mb-3 text-lg font-semibold">已有媒体</h2>
      <form class="grid gap-3 sm:grid-cols-3" @submit.prevent="applyLibraryFilters">
        <label class="field sm:col-span-3"><span>搜索文件名或 Alt</span><input v-model="libraryQuery" type="search" placeholder="输入关键词"></label>
        <label class="field"><span>{{ management ? '素材类型' : '来源' }}</span><select v-model="sourceFilter"><option value="">全部图片</option><option value="upload">上传图片</option><option value="external">外链图片</option></select></label>
        <label class="field"><span>状态</span><select v-model="statusFilter"><option value="active">使用中</option><option value="removed">已移除</option></select></label>
        <div class="flex items-end"><button class="button-secondary" type="submit" :disabled="busy || loadingMore || libraryStatus === 'pending'">应用筛选</button></div>
      </form>
      <div v-if="selectedIds.size" class="admin-batch-bar">
        <span class="text-sm text-ee-primary-strong">已选择已加载的 {{ selectedIds.size }} 项</span>
        <div class="flex gap-2">
          <button class="button-secondary" type="button" :disabled="busy" @click="discardSelected">批量移除</button>
          <button class="button-secondary" type="button" @click="selectedIds = new Set()">取消选择</button>
        </div>
      </div>
    <p v-if="libraryStatus === 'pending'" class="mt-4" role="status">正在读取媒体…</p>
    <div v-if="loadError" class="mt-4"><p role="alert" class="text-ee-danger-ink">媒体读取失败，筛选条件已保留。</p><button type="button" class="button-secondary mt-3" @click="refresh()">重新读取媒体</button></div>
    <div v-if="assets?.length && !loadError && libraryStatus !== 'pending'" class="media-assets-grid mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
      <article v-for="asset in assets" :key="asset.id" class="admin-media-asset">
        <input
          v-if="!asset.deleted_at"
          type="checkbox"
          :checked="selectedIds.has(asset.id)"
          :aria-label="`选择媒体 ${asset.alt_text || asset.original_name}`"
          @change="toggleSelected(asset.id)"
        >
        <img v-if="!brokenImages.has(asset.id)" :src="absoluteUrl(asset.url)" :alt="asset.alt_text" class="size-16 object-cover" @error="brokenImages.add(asset.id)"><div v-else class="media-image-unavailable">图片暂不可预览</div>
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm font-medium">{{ asset.alt_text || asset.original_name }}</p>
          <p class="admin-faint-text mt-1 text-sm">{{ asset.source === 'upload' ? asset.variants.map(item => item.format.toUpperCase()).join(' · ') : '外部链接' }}</p>
          <div class="mt-2 flex flex-wrap gap-2">
            <button v-if="!asset.deleted_at" class="admin-inline-action" type="button" @click="insert(asset)">{{ management ? '复制 Markdown' : '插入 Markdown' }}</button>
            <button v-if="!asset.deleted_at" class="admin-inline-action" type="button" @click="select(asset)">{{ management ? '复制 URL' : '使用 URL' }}</button>
            <button v-if="!asset.deleted_at" class="admin-inline-action text-ee-danger-ink" type="button" :disabled="busy" @click="discard(asset)">移除</button>
            <button v-else class="admin-inline-action" type="button" :disabled="busy" @click="restore(asset)">恢复</button>
          </div>
        </div>
      </article>
    </div>
    <p v-else-if="!loadError && libraryStatus !== 'pending'" class="mt-4 text-sm text-ee-ink-muted">当前筛选下没有媒体。</p>
    <div v-if="hasNext && !loadError && libraryStatus !== 'pending'" class="mt-4 flex justify-center">
      <button class="button-secondary" type="button" :disabled="loadingMore || busy" @click="loadMore">
        {{ loadingMore ? '加载中…' : '加载更多' }}
      </button>
    </div>
    </div>
    <div v-if="!libraryOnly" :id="management ? 'media-add' : undefined" class="media-add">
    <div v-if="!libraryOnly" class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h3 class="text-sm font-semibold">{{ management ? '添加媒体' : '媒体' }}</h3>
        <p class="admin-faint-text mt-1 text-sm">拖放、粘贴或选择图片；自动生成 WebP / AVIF。</p>
      </div>
      <label class="button-secondary cursor-pointer">
        选择图片
        <input
          class="sr-only"
          data-testid="media-file"
          type="file"
          accept="image/jpeg,image/png,image/webp,image/avif"
          multiple
          :disabled="busy"
          @change="selectFiles"
        >
      </label>
    </div>
    <div
      v-if="!libraryOnly"
      class="admin-media-dropzone"
      tabindex="0"
      data-testid="media-dropzone"
      @dragover.prevent
      @drop.prevent="dropFiles"
      @paste="pasteFiles"
    >
      在这里拖放或粘贴图片
    </div>
    <div v-if="!libraryOnly" class="mt-3 grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]">
      <label class="field"><span>Alt 文本</span><input v-model="altText" data-testid="media-alt"></label>
      <label class="field"><span>外部图片 URL</span><input v-model="externalUrl" data-testid="media-external-url" type="url" placeholder="https://…"></label>
      <button class="button-secondary self-end" data-testid="media-external-submit" type="button" :disabled="busy || !externalUrl" @click="registerExternal">
        登记外链
      </button>
    </div>
    <p v-if="!libraryOnly && externalUrl" class="mt-2 text-sm text-ee-warning-ink">
      外链图片不会被下载或托管，原站失效、限流或防盗链时，文章中的图片也会失效。
    </p>
    <p v-if="!libraryOnly" class="admin-upload-state" :class="{ 'admin-upload-state-error': error }" aria-live="polite">
      {{ error || stateLabel }}
    </p>
    <ul v-if="!libraryOnly && uploadResults.length" class="mt-3 space-y-2 text-sm" data-testid="media-upload-results">
      <li
        v-for="result in uploadResults"
        :key="result.file.name"
        class="flex items-center justify-between gap-3 rounded-ee-soft bg-ee-surface-low px-3 py-2"
        :data-status="result.status"
      >
        <span class="truncate">{{ result.file.name }}</span>
        <span :class="result.status === 'error' ? 'text-ee-danger-ink' : 'text-ee-ink-muted'">
          {{ result.status === 'pending' ? '上传中…' : result.status === 'success' ? '已上传' : result.message }}
        </span>
      </li>
    </ul>
    <button
      v-if="!libraryOnly && failedUploads.length"
      class="button-secondary mt-3"
      type="button"
      data-testid="media-retry-failed"
      :disabled="busy"
      @click="retryFailed"
    >
      重试失败项（{{ failedUploads.length }}）
    </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { LifecycleBatchResponse, MediaAsset } from '~/types/api'
import { resolvePublicUrl } from '~/utils/api-url'
import { uploadMediaFiles, type MediaUploadResult } from '~/utils/media-upload'
import { paginatedApiPath, paginationWindow } from '~/utils/pagination'

const emit = defineEmits<{
  insert: [markdown: string]
  selected: [url: string]
}>()
const props = withDefaults(defineProps<{
  management?: boolean
  libraryOnly?: boolean
  showLibraryDefault?: boolean
}>(), {
  management: false,
  libraryOnly: false,
  showLibraryDefault: false,
})
const { libraryOnly } = toRefs(props)
const altText = ref('')
const externalUrl = ref('')
const busy = ref(false)
const loadingMore = ref(false)
const error = ref('')
const libraryError = ref('')
const stateLabel = ref('可上传图片或登记外链。')
const uploadResults = ref<MediaUploadResult[]>([])
const failedUploads = computed(() => uploadResults.value.filter(result => result.status === 'error'))
const pageSize = 12
const showLibrary = ref(props.showLibraryDefault)
const libraryQuery = ref('')
const sourceFilter = ref('')
const brokenImages = reactive(new Set<number>())
const appliedFilters = ref({ source: '', status: 'active', q: '' })
const statusFilter = ref<'active' | 'removed'>('active')
const selectedIds = ref<Set<number>>(new Set())
const fetchPage = async (offset: number) => paginationWindow(
  await apiFetch<MediaAsset[]>(
    `${paginatedApiPath('/admin/media', Math.floor(offset / pageSize) + 1, pageSize)}&${new URLSearchParams({
      status: appliedFilters.value.status,
      ...(appliedFilters.value.source ? { source: appliedFilters.value.source } : {}),
      ...(appliedFilters.value.q ? { q: appliedFilters.value.q } : {}),
    }).toString()}`,
  ),
  pageSize,
)
const mediaDataKey = `media-assets-${useId().replaceAll(':', '-')}`
const { data: mediaPage, refresh, error: loadError, status: libraryStatus } = await useAsyncData(
  mediaDataKey,
  () => showLibrary.value ? fetchPage(0) : Promise.resolve({ items: [], hasNext: false }),
)
const assets = computed(() => mediaPage.value?.items || [])
const hasNext = computed(() => mediaPage.value?.hasNext || false)

const toggleLibrary = async () => {
  showLibrary.value = !showLibrary.value
  if (showLibrary.value) await refresh()
}
const applyLibraryFilters = async () => {
  if (busy.value || loadingMore.value || libraryStatus.value === 'pending') return
  appliedFilters.value = { source: sourceFilter.value, status: statusFilter.value, q: libraryQuery.value.trim() }
  libraryError.value = ''
  selectedIds.value = new Set()
  await refresh()
}

const absoluteUrl = (url: string) => {
  return resolvePublicUrl(url)
}

const upload = async (files: File[], preserveSuccesses = false) => {
  if (!files.length || busy.value) return
  busy.value = true
  error.value = ''
  if (!preserveSuccesses) uploadResults.value = []
  else uploadResults.value = uploadResults.value.filter(result => result.status === 'success')
  const updateResult = async (result: MediaUploadResult) => {
    uploadResults.value = [
      ...uploadResults.value.filter(item => item.file !== result.file),
      result,
    ]
    if (result.status === 'success') await refresh()
  }
  try {
    const results = await uploadMediaFiles(files, async (file) => {
      const body = new FormData()
      body.append('file', file)
      body.append('alt_text', altText.value)
      return apiFetch<MediaAsset>('/admin/media', { method: 'POST', body })
    }, updateResult)
    const succeeded = results.filter(result => result.status === 'success').length
    const failed = results.length - succeeded
    stateLabel.value = `已上传 ${succeeded} 张图片${failed ? `，${failed} 张失败。` : '。'}`
    error.value = failed ? '部分图片上传失败；成功项已保留，可只重试失败项。' : ''
  }
  finally {
    busy.value = false
  }
}

const retryFailed = () => upload(failedUploads.value.map(result => result.file), true)

const selectFiles = async (event: Event) => {
  const input = event.target as HTMLInputElement
  await upload(Array.from(input.files || []))
  input.value = ''
}
const dropFiles = (event: DragEvent) => upload(Array.from(event.dataTransfer?.files || []))
const pasteFiles = (event: ClipboardEvent) => {
  const files = Array.from(event.clipboardData?.items || [])
    .filter(item => item.kind === 'file')
    .map(item => item.getAsFile())
    .filter((file): file is File => file !== null)
  return upload(files)
}
const registerExternal = async () => {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    await apiFetch<MediaAsset>('/admin/media/external', {
      method: 'POST',
      body: { url: externalUrl.value, alt_text: altText.value },
    })
    externalUrl.value = ''
    stateLabel.value = '外部图片已登记。'
    await refresh()
  }
  catch {
    error.value = '外部链接登记失败，请使用有效的 HTTP(S) URL。'
  }
  finally {
    busy.value = false
  }
}
const loadMore = async () => {
  if (loadingMore.value || busy.value || libraryStatus.value === 'pending') return
  libraryError.value = ''
  loadingMore.value = true
  try {
    const next = await fetchPage(assets.value.length)
    mediaPage.value = {
      items: [...assets.value, ...next.items],
      hasNext: next.hasNext,
    }
  }
  catch { libraryError.value = '加载更多失败，请重试。' }
  finally {
    loadingMore.value = false
  }
}
const reloadLibrary = async () => {
  selectedIds.value = new Set()
  await refresh()
}
const toggleSelected = (id: number) => {
  const next = new Set(selectedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedIds.value = next
}
const changeAsset = async (asset: MediaAsset, action: 'discard' | 'restore') => {
  if (busy.value) return
  busy.value = true
  libraryError.value = ''
  try {
    await apiFetch(`/admin/media/${asset.id}/${action}`, { method: 'POST' })
    await reloadLibrary()
  }
  catch { libraryError.value = `${action === 'discard' ? '移除' : '恢复'}失败，请重试。` }
  finally { busy.value = false }
}
const discard = (asset: MediaAsset) => {
  if (!confirm('移除后不会从历史文章中断链，可在“已移除”筛选中恢复。确定继续？')) return
  return changeAsset(asset, 'discard')
}
const restore = (asset: MediaAsset) => changeAsset(asset, 'restore')
const discardSelected = async () => {
  if (!confirm(`移除已加载列表中选中的 ${selectedIds.value.size} 项？公开链接仍会保留。`)) return
  busy.value = true
  error.value = ''
  try {
    const result = await apiFetch<LifecycleBatchResponse>('/admin/media/discard-batch', {
      method: 'POST',
      body: { asset_ids: Array.from(selectedIds.value) },
    })
    const failed = result.results.filter(item => !item.ok)
    libraryError.value = failed.length ? `${failed.length} 项未能移除。` : ''
    await reloadLibrary()
  }
  catch {
    libraryError.value = '批量移除失败，请稍后重试。'
  }
  finally {
    busy.value = false
  }
}
const insert = (asset: MediaAsset) => emit('insert', `\n\n![${asset.alt_text}](${absoluteUrl(asset.url)})\n`)
const select = (asset: MediaAsset) => emit('selected', absoluteUrl(asset.url))
</script>

<style scoped>
.admin-media-uploader--management .media-assets-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 24px; }
.admin-media-uploader--management .admin-media-asset { display: grid; grid-template-columns: minmax(0, 1fr); position: relative; padding: 0 0 20px; border: 0; border-radius: 0; background: none; border-bottom: 1px solid var(--studio-divider); }
.admin-media-uploader--management .admin-media-asset > input { position: absolute; top: 12px; left: 12px; width: 22px; height: 22px; z-index: 1; }
.admin-media-uploader--management .admin-media-asset img { width: 100%; height: 170px; object-fit: cover; border-radius: 7px; background: var(--studio-low); }
.media-image-unavailable { display: grid; place-items: center; min-width: 64px; min-height: 64px; color: var(--ee-ink-muted); background: var(--ee-surface-low); font-size: 14px; }
.admin-media-uploader--management .media-image-unavailable { height: 170px; border-radius: 7px; }
.admin-media-uploader--management .admin-media-asset p { white-space: normal; overflow-wrap: anywhere; }
.admin-media-uploader--management .media-add { scroll-margin-top: 24px; border: 0; border-radius: 0; border-top: 1px solid var(--studio-divider); padding: 28px 0; background: none; }
.admin-media-uploader--management .media-library > form { padding-bottom: 24px; border-bottom: 1px solid var(--studio-divider); }
@media (max-width: 1100px) { .admin-media-uploader--management .media-assets-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 600px) { .admin-media-uploader--management .media-assets-grid { grid-template-columns: minmax(0, 1fr); } }
</style>
