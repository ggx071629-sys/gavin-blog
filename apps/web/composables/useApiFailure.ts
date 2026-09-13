import type { Ref } from 'vue'

export function useApiFailure(error: Ref<unknown>, notFoundMessage?: string): void {
  const toError = (value: unknown) => createError({
    ...pageFailureFromApi(value, notFoundMessage),
    // 客户端路由导航期间，只有 fatal/unhandled 的 Nuxt 错误会被根组件渲染为错误页；
    // 否则初次 setup 失败会变成未处理拒绝，留下旧页面内容。
    // 服务端继续用抛出保持既有 4xx/5xx 状态语义。
    ...(import.meta.client ? { fatal: true } : {}),
  })

  if (error.value) throw toError(error.value)

  watch(error, (value) => {
    if (value) showError(toError(value))
  })
}
