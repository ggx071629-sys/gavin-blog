import { canonicalPageQuery, pageFromQuery } from '~/utils/pagination'

export function useBoundedPage(pageSize: number) {
  const route = useRoute()
  const page = computed(() => pageFromQuery(route.query.page, pageSize))

  watch(() => route.query.page, (rawPage) => {
    if (!import.meta.client) return
    const canonical = canonicalPageQuery(rawPage, pageSize)
    const raw = Array.isArray(rawPage) ? rawPage[0] : rawPage
    if ((raw === undefined && canonical === undefined) || String(raw ?? '') === canonical) return
    const query = { ...route.query }
    if (canonical === undefined) delete query.page
    else query.page = canonical
    void navigateTo({ path: route.path, query, hash: route.hash }, { replace: true })
  }, { immediate: true })

  return page
}
