import { apiErrorStatus } from '../api-errors'
import { mapAssistantCode, parseRetryAfter } from './errors'

export type TrialPhase = 'session' | 'question' | 'stream' | 'restore'
export class TrialHttpError extends Error {
  constructor(public statusCode: number, public code: string, public retryAfter: number | null) {
    super(code)
  }
}

export function trialFailure(cause: unknown, phase: TrialPhase) {
  const error = cause as { data?: { error?: { code?: string } }, response?: { headers?: Headers } } | null
  const status = apiErrorStatus(cause)
  const code = cause instanceof TrialHttpError ? cause.code : error?.data?.error?.code || ''
  const retryAfter = cause instanceof TrialHttpError
    ? cause.retryAfter : parseRetryAfter(error?.response?.headers?.get('Retry-After') ?? null)
  const rejected = !!status && status >= 400 && status < 500
  let message: string
  if (status === 429) {
    const reason = code === 'concurrency_limited' ? '当前已有问题正在处理'
      : code === 'stream_connection_limited' ? '回答连接数已达到限制' : '请求过于频繁'
    message = code === 'budget_exhausted' ? '今日问答预算不足。请查看预算设置。'
      : `${reason}。${retryAfter ? `请等待 ${retryAfter} 秒后再试。` : '请稍后再试。'}`
  }
  else if (code === 'assistant_session_missing' || code === 'assistant_session_expired') {
    message = '试问会话已失效，请重新开始试问。'
  }
  else if (status === 401) message = '管理员登录已失效，请重新登录写作台。'
  else if (code === 'assistant_not_ready' || code === 'assistant_disabled') {
    message = '管理试问当前不可用，请检查试问状态与索引就绪状态。'
  }
  else if (code) {
    const notice = mapAssistantCode(code)
    message = `${notice.title}：${notice.body}`
  }
  else if (status === 403) message = '安全校验失败，请刷新页面后再试。'
  else message = ''

  if (phase === 'restore') {
    message = message || '回答记录读取失败，无法确认后台状态。请刷新回答记录；这不会重新提问。'
  }
  else if (phase === 'session') {
    message = `${message || '无法建立试问会话，请稍后重试。'}本次问题尚未发送。`
  }
  else if (rejected) {
    message = `${message || '本次请求未通过校验。'}本次提问未被接受。`
  }
  else {
    message = message || '回答结果尚未确认，后台可能仍在处理或计费。请刷新回答记录，勿重复发送问题。'
  }
  return { message, retryAfter, rejected }
}
