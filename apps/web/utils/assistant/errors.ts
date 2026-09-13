export type AssistantNotice = {
  kind: 'info' | 'alert'
  title: string
  body: string
  action?: 'retry' | 'resync' | 'restart' | 'refresh'
}

const SCOPE = '这是本站收录的公开内容助手，不会联网搜索，也不会读取站外资料。'

export function mapAssistantCode(code: string): AssistantNotice {
  switch (code) {
    case 'completeness_unverified':
      return { kind: 'info', title: '完整性尚未核验', body: '召回片段不能证明全站完整清单或总数。请限定具体来源或范围，不能将局部结果视为全部。' }
    case 'freshness_unverified':
      return { kind: 'info', title: '时效尚未核验', body: '当前证据未核验全局最新状态或任职时效。请限定来源与事实时间，发布时间不等于事实仍然有效。' }
    case 'clarification_required':
      return { kind: 'info', title: '需要明确对象', body: '请补充具体文章、项目或来源名称。当前无法唯一确定指代对象，明确后再继续回答。' }
    case 'prompt_blocked':
    case 'out_of_scope':
      return { kind: 'info', title: '超出回答范围', body: SCOPE }
    case 'insufficient_evidence':
      return { kind: 'info', title: '证据不足', body: '本站已收录的公开内容不足以回答这个问题。' }
    case 'provider_result_unknown':
      return { kind: 'alert', title: '回答状态未确认', body: '服务未能确认上次回答是否完成。检查结果只读取已有回答，不会重新发送问题。', action: 'refresh' }
    case 'output_invalid':
      return { kind: 'alert', title: '回答格式校验失败', body: '已收到模型输出，但格式不符合要求，未展示该回答。' }
    case 'output_rejected':
      return { kind: 'alert', title: '回答未通过证据校验', body: '已收到模型输出，但事实、相关性或引用未通过校验，不能据此判断本站没有资料。' }
    case 'input_budget_exceeded':
      return { kind: 'alert', title: '回答所需内容超出输入限制', body: '问题、资料或纠正反馈超过输入上限，已停止后续模型调用。需要调整资料选取或输入配置；刷新或原样重发不会解决。' }
    case 'rate_limited':
    case 'concurrency_limited':
    case 'stream_connection_limited':
      return { kind: 'info', title: '请稍后再试', body: '当前请求过于频繁。', action: 'retry' }
    case 'budget_exhausted':
      return { kind: 'info', title: '今日额度已用完', body: '今天的问答额度已经用完。' }
    case 'assistant_disabled':
    case 'assistant_not_ready':
      return { kind: 'info', title: '暂时不可用', body: '公开问答当前不可用。' }
    case 'assistant_session_missing':
    case 'assistant_session_expired':
      return { kind: 'info', title: '会话已失效', body: '可以重新开始一段短会话。', action: 'restart' }
    case 'csrf_failed':
      return { kind: 'alert', title: '需要重新同步', body: '安全校验失败。可以重新同步当前会话，但不会自动重交问题。', action: 'resync' }
    case 'origin_rejected':
      return { kind: 'alert', title: '来源不被允许', body: '当前页面来源无法使用公开问答。' }
    case 'session_revoking':
      return { kind: 'info', title: '正在清除旧会话', body: '旧会话清除已发起，后台仍在完成。这不是旧会话已经清理完成。' }
    default:
      return { kind: 'alert', title: '无法完成这次回答', body: '请稍后再试，不会自动换一种方式重问。' }
  }
}

export function parseRetryAfter(value: string | null): number | null {
  if (!value || !/^[1-9][0-9]*$/.test(value)) return null
  const seconds = Number(value)
  if (!Number.isInteger(seconds) || seconds < 1 || seconds > 86400) return null
  return seconds
}

export function formatPolicyLimits(policy: {
  question_max_chars: number
  session_idle_seconds: number
  session_absolute_seconds: number
  body_retention_seconds: number
}): string {
  const idleMin = Math.round(policy.session_idle_seconds / 60)
  const absoluteHours = Math.round(policy.session_absolute_seconds / 3600)
  const bodyMin = Math.round(policy.body_retention_seconds / 60)
  return `问题最多 ${policy.question_max_chars} 字。短会话空闲约 ${idleMin} 分钟，绝对期限约 ${absoluteHours} 小时。问答正文默认最多保留约 ${bodyMin} 分钟，也可能因容量上限更早清理。`
}
