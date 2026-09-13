import { ORB_GUIDANCE_KEY } from '~/utils/assistant/orb'
import { isAssistantUiEnabled } from '~/utils/assistant/flag'
import { isAssistantLauncherPath } from '~/utils/assistant/allowlist'

export function useAssistantEntry() {
  const config = useRuntimeConfig()
  const route = useRoute()
  const available = useState('assistant-public-available', () => false)
  const visible = computed(() => available.value && isAssistantUiEnabled(config.public.assistantUiEnabled) && isAssistantLauncherPath(route.path))
  const open = useState('assistant-entry-open', () => false)
  const request = useState('assistant-entry-request', () => ({ sequence: 0, source: 'header' as 'header' | 'orb' }))
  const guidanceDismissed = useState('assistant-orb-guidance-dismissed', () => false)
  const finishGuidance = () => {
    guidanceDismissed.value = true
    if (import.meta.client) {
      try { localStorage.setItem(ORB_GUIDANCE_KEY, '1') }
      catch { /* Keep the in-memory preference if storage is blocked. */ }
    }
  }
  const activate = (source: 'header' | 'orb') => {
    if (visible.value) {
      finishGuidance()
      request.value = { sequence: request.value.sequence + 1, source }
    }
  }
  return { visible, open, request, activate, guidanceDismissed, finishGuidance }
}
