export interface PageFailure {
  statusCode: number
  statusMessage: string
}

function numericStatus(value: unknown): number | undefined {
  if (typeof value === 'number' && Number.isInteger(value)) return value
  if (typeof value === 'string' && /^\d{3}$/.test(value)) return Number(value)
  return undefined
}

export function apiErrorDetail(error: unknown): string {
  if (!error || typeof error !== 'object') return ''
  const candidate = error as {
    data?: { detail?: unknown; error?: { message?: unknown } }
    response?: { _data?: { detail?: unknown; error?: { message?: unknown } } }
  }
  const detail = candidate.data?.detail ?? candidate.response?._data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  const message = candidate.data?.error?.message ?? candidate.response?._data?.error?.message
  return typeof message === 'string' ? message : ''
}

export function isOptimisticLockConflict(error: unknown): boolean {
  if (apiErrorStatus(error) !== 409) return false
  return /updated elsewhere/i.test(apiErrorDetail(error))
}

export function isAbortError(error: unknown): boolean {
  if (!error || typeof error !== 'object') return false
  const candidate = error as { name?: string; cause?: unknown }
  if (candidate.name === 'AbortError') return true
  return isAbortError(candidate.cause)
}

export function apiErrorStatus(error: unknown): number | undefined {
  if (!error || typeof error !== 'object') return undefined
  const candidate = error as {
    status?: unknown
    statusCode?: unknown
    response?: { status?: unknown; statusCode?: unknown }
  }
  return numericStatus(candidate.statusCode)
    ?? numericStatus(candidate.status)
    ?? numericStatus(candidate.response?.statusCode)
    ?? numericStatus(candidate.response?.status)
}

export function isApiNetworkFailure(error: unknown): boolean {
  return Boolean(
    error
    && typeof error === 'object'
    && (error as { apiFailureKind?: unknown }).apiFailureKind === 'network',
  )
}

export function pageFailureFromApi(
  error: unknown,
  notFoundMessage = '资源不存在',
): PageFailure {
  const status = apiErrorStatus(error)
  if (status === 404) return { statusCode: 404, statusMessage: notFoundMessage }
  if (status === 401) return { statusCode: 401, statusMessage: '需要登录' }
  if (status === 403) return { statusCode: 403, statusMessage: '请求未通过安全校验' }
  if (status === 429) return { statusCode: 429, statusMessage: '请求过于频繁' }
  if (status && status >= 500 && status <= 599) {
    return { statusCode: status, statusMessage: '上游服务暂时不可用' }
  }
  return { statusCode: 503, statusMessage: '上游服务暂时不可用' }
}

export function loginFailureMessage(error: unknown): string {
  if (isApiNetworkFailure(error)) return '无法连接登录服务，请检查网络后重试。'
  const status = apiErrorStatus(error)
  if (status === 401) return '用户名或密码不正确。'
  if (status === 403) return '安全校验失败，请刷新页面后重试。'
  if (status === 429) return '尝试次数过多，请稍后再试。'
  if (status && status >= 500) return '登录服务暂时不可用，请稍后重试。'
  return '无法连接登录服务，请检查网络后重试。'
}

export function logoutFailureMessage(error: unknown): string {
  if (isApiNetworkFailure(error)) {
    return '无法连接退出服务，会话仍可能有效。请检查网络后重试。'
  }
  const status = apiErrorStatus(error)
  if (status === 403) return '退出未通过安全校验，会话仍可能有效。请刷新页面后重试。'
  if (status === 429) return '退出请求过于频繁，会话仍可能有效。请稍后重试。'
  if (status && status >= 500) return '退出服务暂时不可用，会话仍可能有效。请稍后重试。'
  return '无法连接退出服务，会话仍可能有效。请检查网络后重试。'
}

export function safeAdminReturnTo(value: unknown): string {
  if (typeof value !== 'string') return '/admin/articles'
  try {
    const target = new URL(value, 'https://local.invalid')
    const isLocal = target.origin === 'https://local.invalid'
    const isAdmin = target.pathname === '/admin' || target.pathname.startsWith('/admin/')
    const isLogin = target.pathname === '/admin/login'
    if (!isLocal || !isAdmin || isLogin) return '/admin/articles'
    return `${target.pathname}${target.search}${target.hash}`
  }
  catch {
    return '/admin/articles'
  }
}
