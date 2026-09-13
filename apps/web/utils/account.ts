import { apiErrorDetail, apiErrorStatus } from './api-errors'

export function accountRetryAfter(error: unknown): number {
  const response = (error as { response?: { headers?: Headers } } | null)?.response
  const seconds = Number(response?.headers?.get('Retry-After'))
  return Number.isFinite(seconds) && seconds > 0 ? Math.ceil(seconds) : 0
}

export function accountFailureMessage(error: unknown): string {
  const status = apiErrorStatus(error)
  if (status === 401) return '登录已失效，请重新登录。'
  if (status === 403) return '安全校验失败，请刷新页面后重试。'
  if (status === 429) {
    const wait = accountRetryAfter(error)
    return wait ? `操作过于频繁，请在 ${wait} 秒后重试。` : '操作过于频繁，请稍后重试。'
  }
  const detail = apiErrorDetail(error)
  if (detail === 'invalid_current_password') return '当前密码不正确，请重新输入。'
  if (detail === 'invalid_code') return '验证码错误、已过期或已使用，请核对或重新发送。'
  if (detail === 'mail_unavailable') return '邮件暂不可用，未确认发送成功，请稍后重试。'
  if (status === 422) return '密码或验证码不符合要求：密码须为 15–128 个字符，不能为弱密码或与当前密码相同；验证码须为 6 位数字。'
  return '操作未确认成功，请检查网络后重试。'
}
