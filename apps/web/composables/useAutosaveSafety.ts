import { onBeforeUnmount, onMounted } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'

import type { AutosaveQueue } from '~/utils/autosave'
import {
  flushAutosaveBeforeNavigation,
  preventUnloadWhenAutosaveIsDirty,
} from '~/utils/autosave'

export const useAutosaveSafety = <T>(
  queue: AutosaveQueue<T>,
  onError?: (error: unknown) => void,
) => {
  const flushBeforeNavigation = () => flushAutosaveBeforeNavigation(queue, onError)
  const onBeforeUnload = (event: BeforeUnloadEvent) => {
    preventUnloadWhenAutosaveIsDirty(event, queue)
  }

  onBeforeRouteLeave(flushBeforeNavigation)
  onMounted(() => window.addEventListener('beforeunload', onBeforeUnload))
  onBeforeUnmount(() => {
    window.removeEventListener('beforeunload', onBeforeUnload)
    void queue.dispose().catch(error => onError?.(error))
  })

  return { flushBeforeNavigation }
}
