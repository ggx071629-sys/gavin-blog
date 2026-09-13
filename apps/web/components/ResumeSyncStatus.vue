<template>
  <section class="resume-sync" aria-labelledby="resume-sync-heading" data-testid="resume-sync">
    <h3 id="resume-sync-heading">助手使用的简历</h3>
    <p>首次填写或更换地址后，保存设置会自动导入。同一地址换了 PDF 后，点击“立即刷新”。</p>
    <div aria-live="polite" aria-atomic="true">
      <p v-if="loadError" role="alert">暂时无法读取同步状态，请重试。</p>
      <p v-else-if="!view">正在读取同步状态…</p>
      <template v-else>
        <p class="resume-sync-state" data-testid="resume-sync-state">{{ labels[view.state] }}</p>
        <p v-if="view.state !== 'unconfigured'">{{ view.usable ? '助手当前可使用已同步的简历。' : '助手当前不使用简历证据。' }}</p>
        <p v-if="view.error_code" role="alert">{{ errorHint }}</p>
        <p v-if="view.retry_at">已安排重试：{{ time(view.retry_at) }}</p>
      </template>
    </div>
    <dl v-if="view && !loadError" class="resume-sync-times">
      <div><dt>最后成功检查</dt><dd>{{ time(view.last_checked_at) }}</dd></div>
      <div><dt>最后成功索引</dt><dd>{{ time(view.last_indexed_at) }}</dd></div>
    </dl>
    <p v-if="urlDirty" class="resume-sync-notice">简历地址尚未保存，请先点击“保存设置”。</p>
    <p v-if="conflict" role="alert">简历地址已在别处修改，请重新载入个人名片后再刷新。</p>
    <p v-if="actionMessage" role="status">{{ actionMessage }}</p>
    <div class="resume-sync-actions">
      <button type="button" class="button-secondary" :disabled="disabled" data-testid="resume-refresh" @click="refreshResume">
        {{ refreshing ? '提交中…' : '立即刷新' }}
      </button>
      <button v-if="loadError" type="button" class="button-secondary" @click="load">重试读取状态</button>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { ResumeStatus } from '~/types/resume'
import { apiErrorStatus } from '~/utils/api-errors'

const props = defineProps<{ savedUrl: string | null | undefined; draftUrl: string | null | undefined; revision: number }>()
const view = ref<ResumeStatus | null>(null)
const loadError = ref(false)
const refreshing = ref(false)
const conflict = ref(false)
const cooling = ref(false)
const actionMessage = ref('')
const urlDirty = computed(() => (props.draftUrl || '').trim() !== (props.savedUrl || '').trim())
const busy = computed(() => Boolean(view.value && (['pending', 'checking', 'parsing', 'indexing'].includes(view.value.state) || view.value.retry_at)))
const disabled = computed(() => !view.value || !props.savedUrl || urlDirty.value || conflict.value || loadError.value || refreshing.value || cooling.value || busy.value)
const labels: Record<ResumeStatus['state'], string> = {
  unconfigured: '尚未配置简历', pending: '已排队，等待同步', checking: '正在检查文件',
  parsing: '正在提取文字', indexing: '正在建立索引', ready: '同步完成', failed: '同步失败',
}
const hints: Record<string, string> = {
  blocked_host: '文件域名尚未获准下载，请配置允许的域名后重试。',
  download_timeout: '下载超时，简历证据已暂停。', download_failed: '下载失败，请检查文件链接是否可公开访问。',
  too_large: 'PDF 超过 10 MiB，请提供更小的文件。', not_pdf: '链接未返回 PDF 文件，请检查下载地址。',
  too_many_pages: 'PDF 超过 20 页，请提供精简版本。', encrypted_pdf: '无法导入加密 PDF，请提供未加密版本。',
  text_unavailable: '无法提取完整文字，请提供可复制文字的 PDF；暂不支持扫描件。',
  parse_failed: 'PDF 解析失败，请重新导出文件后刷新。', parser_unavailable: '解析服务暂不可用，请检查服务配置后重试。',
  parse_timeout: 'PDF 解析超时，请简化文件后重试。', text_too_large: '提取文字过长，请提供精简版本。',
  index_failed: '文件已检查，但建立索引失败，请重试。',
}
const errorHint = computed(() => hints[view.value?.error_code || ''] || '同步未完成，请检查文件后重试。')
const time = (value: string | null | undefined) => value
  ? new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false })
  : '尚无记录'
let baselineEpoch: number | null = null
let serial = 0
let active = false
let poll: ReturnType<typeof setTimeout> | undefined
let cooldown: ReturnType<typeof setTimeout> | undefined
let controller: AbortController | undefined

function schedule() {
  clearTimeout(poll)
  if (active && busy.value) poll = setTimeout(() => {
    if (document.visibilityState === 'visible') void load()
    else schedule()
  }, 5000)
}

async function load() {
  if (!active) return
  const id = ++serial
  controller?.abort()
  controller = new AbortController()
  try {
    const result = await apiFetch<ResumeStatus>('/admin/profile/resume', { signal: controller.signal, retry: 0 })
    if (!active || id !== serial) return
    if (baselineEpoch !== null && result.binding_epoch !== baselineEpoch) conflict.value = true
    if (baselineEpoch === null) baselineEpoch = result.binding_epoch
    view.value = result
    loadError.value = false
  }
  catch {
    if (active && id === serial) loadError.value = true
  }
  finally { if (active && id === serial) schedule() }
}

async function refreshResume() {
  if (disabled.value || !view.value) return
  refreshing.value = true
  actionMessage.value = ''
  const id = ++serial
  controller?.abort()
  clearTimeout(poll)
  try {
    const result = await apiFetch<ResumeStatus>('/admin/profile/resume/refresh', {
      method: 'POST', body: { binding_epoch: view.value.binding_epoch }, retry: 0,
    })
    if (!active || id !== serial) return
    view.value = result
    actionMessage.value = '刷新请求已排队，完成后会更新同步状态。'
  }
  catch (error) {
    if (!active || id !== serial) return
    if (apiErrorStatus(error) === 409) conflict.value = true
    else if (apiErrorStatus(error) === 429) {
      const raw = (error as { response?: { headers?: Headers } }).response?.headers?.get('Retry-After')
      const seconds = Math.min(3600, Math.max(1, Number(raw) || 60))
      cooling.value = true
      actionMessage.value = `刷新过于频繁，请等待 ${seconds} 秒后再试。`
      cooldown = setTimeout(() => { cooling.value = false; actionMessage.value = '' }, seconds * 1000)
    }
    else actionMessage.value = '刷新请求未成功提交，请稍后重试。'
  }
  finally {
    refreshing.value = false
    schedule()
  }
}

watch(() => [props.savedUrl, props.revision], () => {
  baselineEpoch = null
  conflict.value = false
  actionMessage.value = ''
  view.value = null
  void load()
})
function onVisibility() { if (document.visibilityState === 'visible' && busy.value) void load() }
onMounted(() => { active = true; void load(); document.addEventListener('visibilitychange', onVisibility) })
onBeforeUnmount(() => {
  active = false
  serial++
  controller?.abort()
  clearTimeout(poll)
  clearTimeout(cooldown)
  document.removeEventListener('visibilitychange', onVisibility)
})
</script>

<style scoped>
.resume-sync { border: 1px solid var(--studio-divider); padding: 20px; background: var(--studio-low); overflow-wrap: anywhere; }
.resume-sync h3 { font-weight: 600; font-size: 16px; }
.resume-sync p { margin-top: 10px; color: var(--studio-muted); font-size: 14px; line-height: 1.7; }
.resume-sync .resume-sync-state { color: var(--studio-ink); font-weight: 600; }
.resume-sync-times { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-top: 16px; font-size: 13px; }
.resume-sync-times dt { color: var(--studio-muted); }
.resume-sync-times dd { margin: 6px 0 0; }
.resume-sync-actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 16px; }
@media (max-width: 600px) { .resume-sync-times { grid-template-columns: minmax(0, 1fr); } }
</style>
