import type { AssistantErrorEnvelope, AssistantSessionCreateResponse, AssistantSessionStatusResponse } from '~/types/api'
import { AssistantSseError, type AssistantPublicEvent, type AssistantSseParser } from './sse'
import { sameOriginApiBase } from './origin'
import { closeAnswerCitations } from './citations'

const ERROR_LIMIT = 16 * 1024

export class AssistantHttpError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    readonly retryAfter: string | null,
  ) {
    super(code)
  }
}

export function readAssistantCsrf(): string {
  const match = document.cookie.match(/(?:^|; )gavin_assistant_csrf=([^;]*)/)
  return match ? decodeURIComponent(match[1]!) : ''
}

export function assertResponseUrl(response: Response, expectedPath: string, origin: string) {
  const url = new URL(response.url)
  const expected = new URL(expectedPath, origin)
  if (
    url.origin !== expected.origin
    || url.pathname !== expected.pathname
    || url.search !== ''
    || url.hash !== ''
  ) {
    throw new AssistantHttpError(0, 'origin_rejected', null)
  }
}

function contentEssence(value: string | null): string {
  return (value || '').split(';', 1)[0]!.trim().toLowerCase()
}

async function readError(response: Response): Promise<AssistantHttpError> {
  const type = contentEssence(response.headers.get('content-type'))
  if (type !== 'application/json') throw new AssistantHttpError(response.status, 'invalid_request', null)
  const buffer = await response.arrayBuffer()
  if (buffer.byteLength > ERROR_LIMIT) throw new AssistantHttpError(response.status, 'invalid_request', null)
  let parsed: AssistantErrorEnvelope
  try {
    parsed = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(buffer)) as AssistantErrorEnvelope
  }
  catch {
    throw new AssistantHttpError(response.status, 'invalid_request', null)
  }
  if (!parsed?.error || typeof parsed.error.code !== 'string' || typeof parsed.error.message !== 'string') {
    throw new AssistantHttpError(response.status, 'invalid_request', null)
  }
  if (Object.keys(parsed).length !== 1 || Object.keys(parsed.error).length !== 2) {
    throw new AssistantHttpError(response.status, 'invalid_request', null)
  }
  return new AssistantHttpError(response.status, parsed.error.code, response.headers.get('Retry-After'))
}

export async function assistantRequest(
  path: string,
  init: RequestInit,
  origin: string,
  apiBase: string,
): Promise<Response> {
  if (!sameOriginApiBase(apiBase, origin)) throw new AssistantHttpError(0, 'origin_rejected', null)
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    credentials: 'include',
    redirect: 'error',
  })
  assertResponseUrl(response, `${apiBase}${path}`, origin)
  return response
}

export async function bootstrapSession(origin: string, apiBase: string, signal?: AbortSignal): Promise<AssistantSessionCreateResponse> {
  const response = await assistantRequest('/assistant/sessions', { method: 'POST', signal }, origin, apiBase)
  if (!response.ok) throw await readError(response)
  if (contentEssence(response.headers.get('content-type')) !== 'application/json') {
    throw new AssistantHttpError(response.status, 'invalid_request', null)
  }
  return await response.json() as AssistantSessionCreateResponse
}

export async function loadSession(origin: string, apiBase: string, signal?: AbortSignal): Promise<AssistantSessionStatusResponse> {
  const response = await assistantRequest('/assistant/session', { method: 'GET', signal }, origin, apiBase)
  if (!response.ok) throw await readError(response)
  if (contentEssence(response.headers.get('content-type')) !== 'application/json') {
    throw new AssistantHttpError(response.status, 'invalid_request', null)
  }
  return parseSessionStatus(await response.json())
}

const exactKeys = (value: Record<string, unknown>, keys: string[]) => {
  const actual = Object.keys(value).sort()
  const expected = [...keys].sort()
  return actual.length === expected.length && actual.every((key, index) => key === expected[index])
}

function parsePolicy(value: unknown) {
  if (!value || typeof value !== 'object') return null
  const row = value as Record<string, unknown>
  const keys = ['question_max_chars', 'session_idle_seconds', 'session_absolute_seconds', 'body_retention_seconds']
  if (!exactKeys(row, keys)) return null
  if (!keys.every(key => Number.isInteger(row[key]) && Number(row[key]) > 0)) return null
  return row as unknown as AssistantSessionStatusResponse['policy']
}

function parseTurn(value: unknown): AssistantSessionStatusResponse['turns'][number] | null {
  if (!value || typeof value !== 'object') return null
  const row = value as Record<string, unknown>
  const keys = ['turn_id', 'created_at', 'status', 'code', 'message', 'question', 'answer', 'citations', 'sources', 'body_available']
  if ('feedback' in row) {
    keys.push('feedback')
    if (row.feedback !== null && row.feedback !== 'helpful' && row.feedback !== 'unhelpful') return null
    if ((!row.body_available || row.status !== 'answer') && row.feedback !== null) return null
  }
  if (!exactKeys(row, keys)) return null
  if (typeof row.turn_id !== 'string' || typeof row.created_at !== 'string' || typeof row.body_available !== 'boolean') return null
  for (const key of ['status', 'code', 'message', 'question', 'answer'] as const) {
    if (row[key] !== null && typeof row[key] !== 'string') return null
  }
  if (!row.body_available) {
    if (row.question !== null || row.answer !== null || row.message !== null || row.citations !== null || row.sources !== null) return null
    return row as unknown as AssistantSessionStatusResponse['turns'][number]
  }
  if (row.status === 'answer') {
    const closed = closeAnswerCitations(String(row.answer || ''), row.citations, row.sources)
    if (!closed) {
      return {
        ...(row as unknown as AssistantSessionStatusResponse['turns'][number]),
        answer: null,
        citations: null,
        sources: null,
        message: null,
        body_available: false,
        feedback: null,
      }
    }
  }
  else if (row.citations !== null || row.sources !== null || row.answer !== null) return null
  return row as unknown as AssistantSessionStatusResponse['turns'][number]
}

export function parseSessionStatus(value: unknown): AssistantSessionStatusResponse {
  if (!value || typeof value !== 'object') throw new AssistantHttpError(200, 'invalid_request', null)
  const row = value as Record<string, unknown>
  const keys = ['session_id', 'created_at', 'idle_expires_at', 'absolute_expires_at', 'policy', 'turns', 'active_turn']
  if (!exactKeys(row, keys)) throw new AssistantHttpError(200, 'invalid_request', null)
  if (![row.session_id, row.created_at, row.idle_expires_at, row.absolute_expires_at].every(value => typeof value === 'string')) {
    throw new AssistantHttpError(200, 'invalid_request', null)
  }
  const policy = parsePolicy(row.policy)
  if (!policy || !Array.isArray(row.turns)) throw new AssistantHttpError(200, 'invalid_request', null)
  const turns = row.turns.map(parseTurn)
  if (turns.some(turn => turn === null)) throw new AssistantHttpError(200, 'invalid_request', null)
  let activeTurn = null
  if (row.active_turn !== null) {
    if (!row.active_turn || typeof row.active_turn !== 'object') throw new AssistantHttpError(200, 'invalid_request', null)
    const active = row.active_turn as Record<string, unknown>
    if (!exactKeys(active, ['turn_id', 'question', 'created_at', 'stage'])) throw new AssistantHttpError(200, 'invalid_request', null)
    if (typeof active.turn_id !== 'string' || typeof active.created_at !== 'string') throw new AssistantHttpError(200, 'invalid_request', null)
    if (active.question !== null && typeof active.question !== 'string') throw new AssistantHttpError(200, 'invalid_request', null)
    if (active.stage !== null && !['checking', 'retrieving', 'composing', 'validating'].includes(String(active.stage))) {
      throw new AssistantHttpError(200, 'invalid_request', null)
    }
    activeTurn = active as unknown as AssistantSessionStatusResponse['active_turn']
  }
  return {
    session_id: row.session_id as string,
    created_at: row.created_at as string,
    idle_expires_at: row.idle_expires_at as string,
    absolute_expires_at: row.absolute_expires_at as string,
    policy,
    turns: turns as AssistantSessionStatusResponse['turns'],
    active_turn: activeTurn,
  }
}

export async function saveFeedback(origin: string, apiBase: string, turnId: string, value: 'helpful' | 'unhelpful' | null, signal?: AbortSignal) {
  const response = await assistantRequest(`/assistant/turns/${encodeURIComponent(turnId)}/feedback`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json', 'X-Assistant-CSRF': readAssistantCsrf() },
    body: JSON.stringify({ value }), signal,
  }, origin, apiBase)
  if (!response.ok) throw await readError(response)
  if (contentEssence(response.headers.get('content-type')) !== 'application/json') throw new AssistantHttpError(200, 'invalid_request', null)
  const result = await response.json()
  if (!result || !exactKeys(result, ['turn_id', 'value']) || result.turn_id !== turnId || result.value !== value) throw new AssistantHttpError(200, 'invalid_request', null)
  return value
}

export async function deleteSession(origin: string, apiBase: string, signal?: AbortSignal): Promise<{ status: number, code?: string }> {
  const response = await assistantRequest('/assistant/session', {
    method: 'DELETE',
    headers: { 'X-Assistant-CSRF': readAssistantCsrf() },
    signal,
  }, origin, apiBase)
  if (response.status === 204) return { status: 204 }
  if (response.status === 202) {
    const error = await readError(response)
    return { status: 202, code: error.code }
  }
  throw await readError(response)
}

export async function* streamQuestion(
  origin: string,
  apiBase: string,
  payload: { question: string, current_path: string },
  key: string,
  lastEventId: number | null,
  parser: AssistantSseParser,
  signal: AbortSignal,
): AsyncGenerator<AssistantPublicEvent> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Assistant-CSRF': readAssistantCsrf(),
    'Idempotency-Key': key,
  }
  if (lastEventId && lastEventId > 0) headers['Last-Event-ID'] = String(lastEventId)
  const response = await assistantRequest('/assistant/questions', {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
    signal,
  }, origin, apiBase)
  if (!response.ok) throw await readError(response)
  if (contentEssence(response.headers.get('content-type')) !== 'text/event-stream') {
    throw new AssistantHttpError(response.status, 'invalid_request', null)
  }
  if (!response.body) throw new AssistantSseError('missing_body')
  const reader = response.body.getReader()
  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      parser.finish()
      return
    }
    for (const event of parser.push(value)) yield event
  }
}
