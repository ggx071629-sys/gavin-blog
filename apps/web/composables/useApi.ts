import type { UseFetchOptions } from 'nuxt/app'
import { apiErrorStatus, isAbortError } from '~/utils/api-errors'
import { serverApiBase } from '~/utils/api-url'

export async function apiFetch<T>(
  path: string,
  options: UseFetchOptions<T> & { method?: string; signal?: AbortSignal } = {},
): Promise<T> {
  const config = useRuntimeConfig()
  const csrf = useCookie<string | null>('gavin_csrf')
  const requestHeaders = import.meta.server ? useRequestHeaders(['cookie']) : {}
  const headers = new Headers(options.headers as HeadersInit | undefined)
  if (requestHeaders.cookie) {
    headers.set('cookie', requestHeaders.cookie)
  }
  if (options.method && !['GET', 'HEAD'].includes(options.method.toUpperCase()) && csrf.value) {
    headers.set('X-CSRF-Token', csrf.value)
  }
  try {
    return await $fetch<T>(path, {
      ...options,
      baseURL: import.meta.server ? serverApiBase(config.apiUpstream) : config.public.apiBase,
      credentials: 'include',
      headers,
    } as never) as T
  }
  catch (error: unknown) {
    if (isAbortError(error)) throw error
    if (apiErrorStatus(error) !== undefined) throw error
    const unavailable = new Error('API service unavailable', { cause: error }) as Error & {
      apiFailureKind: 'network'
      status: number
      statusCode: number
    }
    unavailable.apiFailureKind = 'network'
    unavailable.status = 503
    unavailable.statusCode = 503
    throw unavailable
  }
}
