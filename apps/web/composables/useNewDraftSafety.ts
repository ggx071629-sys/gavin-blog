import { onBeforeRouteLeave } from 'vue-router'

/** New content has no server identity yet; never claim it was autosaved. */
export const useNewDraftSafety = (read: () => unknown) => {
  const initial = JSON.stringify(read())
  const created = ref(false)
  const dirty = () => !created.value && JSON.stringify(read()) !== initial
  onBeforeRouteLeave(() => !dirty() || window.confirm('草稿尚未创建，离开会丢失当前输入。仍要离开？'))
  const beforeUnload = (event: BeforeUnloadEvent) => {
    if (!dirty()) return
    event.preventDefault()
    event.returnValue = ''
  }
  onMounted(() => window.addEventListener('beforeunload', beforeUnload))
  onBeforeUnmount(() => window.removeEventListener('beforeunload', beforeUnload))
  return { created }
}
