import { describe, expect, it } from 'vitest'
import { accountFailureMessage, accountRetryAfter } from '../../utils/account'

describe('account feedback', () => {
  it('maps security errors without exposing backend details', () => {
    expect(accountFailureMessage({ status: 400, data: { detail: 'invalid_current_password' } })).toContain('当前密码不正确')
    expect(accountFailureMessage({ status: 400, data: { detail: 'invalid_code' } })).toContain('已过期或已使用')
    expect(accountFailureMessage({ status: 422 })).toContain('15–128')
    expect(accountFailureMessage({ status: 403 })).toContain('安全校验失败')
    expect(accountFailureMessage({ status: 401 })).toContain('登录已失效')
    expect(accountFailureMessage({ status: 503, data: { detail: 'smtp authorization confidential' } })).not.toContain('confidential')
    expect(accountFailureMessage({ status: 503, data: { detail: 'mail_unavailable' } })).toContain('未确认发送成功')
  })
  it('honors server retry seconds and rejects invalid values', () => {
    const error = { status: 429, response: { headers: new Headers({ 'Retry-After': '61' }) } }
    expect(accountRetryAfter(error)).toBe(61)
    expect(accountFailureMessage(error)).toContain('61 秒')
    for (const value of ['-1', 'invalid', 'Infinity']) {
      expect(accountRetryAfter({ response: { headers: new Headers({ 'Retry-After': value }) } })).toBe(0)
    }
  })
})
