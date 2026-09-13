import { isAssistantUiEnabled } from '~/utils/assistant/flag'

/** One poll owner in the public layout; shared state is consumed by both entries. */
export function useAssistantAvailability() {
  const available = useState('assistant-public-available', () => false)
  const config = useRuntimeConfig()
  const route = useRoute()
  let timer: ReturnType<typeof setTimeout> | undefined
  let revision = 0
  let disposed = false
  const refresh = async () => {
    clearTimeout(timer)
    const current = ++revision
    if (disposed || !isAssistantUiEnabled(config.public.assistantUiEnabled)) return
    if (document.visibilityState !== 'visible') return
    try {
      const result = await apiFetch<{ available: boolean }>('/assistant/availability', {
        signal: AbortSignal.timeout(5000),
      })
      if (current === revision && !disposed) available.value = result.available === true
    }
    catch { if (current === revision) available.value = false }
    finally { if (!disposed && current === revision) timer = setTimeout(refresh, 25000) }
  }
  onMounted(() => { void refresh(); document.addEventListener('visibilitychange', refresh) })
  watch(() => route.path, () => { if (import.meta.client) void refresh() })
  onBeforeUnmount(() => {
    disposed = true
    revision++
    clearTimeout(timer)
    document.removeEventListener('visibilitychange', refresh)
    available.value = false
  })
  return available
}
