import { describe, expect, it } from 'vitest'
import {
  apiErrorDetail,
  apiErrorStatus,
  isOptimisticLockConflict,
  loginFailureMessage,
  logoutFailureMessage,
  pageFailureFromApi,
  safeAdminReturnTo,
} from '../../utils/api-errors'

describe('API failure classification', () => {
  it('distinguishes optimistic-lock 409 from slug-lock 409', () => {
    expect(apiErrorDetail({ data: { detail: 'published article slug cannot be changed' } })).toContain('cannot be changed')
    expect(isOptimisticLockConflict({ statusCode: 409, data: { detail: 'article was updated elsewhere' } })).toBe(true)
    expect(isOptimisticLockConflict({ statusCode: 409, data: { detail: 'published article slug cannot be changed' } })).toBe(false)
    expect(isOptimisticLockConflict({ statusCode: 409 })).toBe(false)
  })

  it('reads statuses from Nuxt and fetch error shapes', () => {
    expect(apiErrorStatus({ statusCode: 401 })).toBe(401)
    expect(apiErrorStatus({ status: '403' })).toBe(403)
    expect(apiErrorStatus({ response: { status: 429 } })).toBe(429)
    expect(apiErrorStatus(new Error('offline'))).toBeUndefined()
  })

  it('only maps an explicit 404 to not found', () => {
    expect(pageFailureFromApi({ statusCode: 404 }, '文章不存在')).toEqual({
      statusCode: 404,
      statusMessage: '文章不存在',
    })
    expect(pageFailureFromApi({ statusCode: 500 }).statusCode).toBe(500)
    expect(pageFailureFromApi({ statusCode: 403 }).statusCode).toBe(403)
    expect(pageFailureFromApi({ statusCode: 429 }).statusCode).toBe(429)
    expect(pageFailureFromApi(new Error('offline')).statusCode).toBe(503)
  })

  it('gives truthful login messages', () => {
    expect(loginFailureMessage({ statusCode: 401 })).toContain('用户名或密码')
    expect(loginFailureMessage({ statusCode: 403 })).toContain('安全校验')
    expect(loginFailureMessage({ statusCode: 429 })).toContain('次数过多')
    expect(loginFailureMessage({ statusCode: 500 })).toContain('暂时不可用')
    expect(loginFailureMessage({ statusCode: 503, apiFailureKind: 'network' })).toContain('无法连接')
  })

  it('never claims logout succeeded after a failed request', () => {
    expect(logoutFailureMessage({ statusCode: 403 })).toContain('会话仍可能有效')
    expect(logoutFailureMessage({ statusCode: 500 })).toContain('暂时不可用')
    expect(logoutFailureMessage({ statusCode: 503, apiFailureKind: 'network' })).toContain('无法连接')
  })

  it('accepts only local admin return targets', () => {
    expect(safeAdminReturnTo('/admin/projects?page=2')).toBe('/admin/projects?page=2')
    expect(safeAdminReturnTo('/admin')).toBe('/admin')
    expect(safeAdminReturnTo('/admin/login')).toBe('/admin/articles')
    expect(safeAdminReturnTo('//evil.example/admin')).toBe('/admin/articles')
    expect(safeAdminReturnTo('https://evil.example/admin')).toBe('/admin/articles')
    expect(safeAdminReturnTo('/projects')).toBe('/admin/articles')
  })
})
