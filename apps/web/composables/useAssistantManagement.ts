import type { AssistantAdminSnapshot } from '~/types/api'
import type { AssistantManagement, SyncTasks } from '~/utils/assistant-management'
import { parseAssistantSnapshot } from '~/utils/assistant-admin'
import { apiErrorDetail } from '~/utils/api-errors'

export function useAssistantManagement() {
  const snapshot = shallowRef<AssistantAdminSnapshot | null>(null)
  const management = shallowRef<AssistantManagement | null>(null)
  const tasks = shallowRef<SyncTasks | null>(null)
  const loading = ref(false)
  const mutating = ref(false)
  const stale = ref(false)
  const error = ref('')
  const success = ref('')
  const filter = ref('')
  const offset = ref(0)
  let revision = 0
  let disposed = false
  let timer: ReturnType<typeof setTimeout> | undefined
  const taskUrl = () => `/admin/assistant/sync?limit=10&offset=${offset.value}${filter.value ? `&status=${filter.value}` : ''}`
  const load = async () => {
    clearTimeout(timer)
    const current = ++revision
    loading.value = true
    try {
      const [raw, details, sync] = await Promise.all([
        apiFetch<unknown>('/admin/assistant'), apiFetch<AssistantManagement>('/admin/assistant/management'),
        apiFetch<SyncTasks>(taskUrl()),
      ])
      if (current !== revision || disposed) return
      snapshot.value = parseAssistantSnapshot(raw)
      management.value = details
      tasks.value = sync
      stale.value = false
    }
    catch (cause) {
      if (current !== revision || disposed) return
      stale.value = true
      error.value = apiErrorDetail(cause) || '读取失败，请刷新状态。上次结果可能已过期。'
    }
    finally {
      if (current === revision) {
        loading.value = false
        if (!disposed && import.meta.client && document.visibilityState === 'visible') timer = setTimeout(load, 15000)
      }
    }
  }
  const refresh = async () => { error.value = ''; await load() }
  const mutate = async (action: () => Promise<unknown>, message: string) => {
    if (mutating.value) return false
    revision++
    mutating.value = true
    error.value = ''; success.value = ''
    try { await action(); success.value = message; await load(); return true }
    catch (cause) { error.value = apiErrorDetail(cause) || '操作未完成，请刷新状态后重试。'; return false }
    finally { mutating.value = false }
  }
  const visibility = () => { if (document.visibilityState === 'visible') void load(); else { clearTimeout(timer); revision++; loading.value = false } }
  onMounted(() => { void load(); document.addEventListener('visibilitychange', visibility) })
  onBeforeUnmount(() => { disposed = true; revision++; clearTimeout(timer); document.removeEventListener('visibilitychange', visibility) })
  watch([filter, offset], load)
  return { snapshot, management, tasks, loading, mutating, stale, error, success, filter, offset, load, refresh, mutate }
}
