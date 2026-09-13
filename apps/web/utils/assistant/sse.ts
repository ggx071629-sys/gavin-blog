export const ASSISTANT_MAX_EVENTS = 16
export const ASSISTANT_MAX_TURN_BYTES = 256 * 1024
export const ASSISTANT_MAX_EVENT_BYTES = 64 * 1024
export const ASSISTANT_MAX_RESIDUAL_BYTES = 64 * 1024

const STAGES = new Set(['checking', 'retrieving', 'composing', 'validating'])
const TERMINALS = new Set(['answer', 'refusal', 'error'])
const STAGE_FIELDS = new Set(['event_id', 'turn_id', 'stage'])
const REFUSAL_FIELDS = new Set(['event_id', 'turn_id', 'type', 'code', 'message'])
const ANSWER_FIELDS = new Set(['event_id', 'turn_id', 'type', 'code', 'message', 'answer', 'citations', 'sources'])

export class AssistantSseError extends Error {
  readonly reason: string

  constructor(reason: string) {
    super(reason)
    this.reason = reason
  }
}

export type AssistantStageEvent = {
  event: 'checking' | 'retrieving' | 'composing' | 'validating'
  event_id: number
  turn_id: string
  stage: 'checking' | 'retrieving' | 'composing' | 'validating'
}

export type AssistantTerminalEvent = {
  event: 'answer' | 'refusal' | 'error'
  event_id: number
  turn_id: string
  type: 'answer' | 'refusal' | 'error'
  code: string
  message: string
  answer?: string
  citations?: unknown
  sources?: unknown
}

export type AssistantPublicEvent = AssistantStageEvent | AssistantTerminalEvent

export class AssistantSseParser {
  private decoder = new TextDecoder('utf-8', { fatal: true })
  private residual = ''
  private eventCount = 0
  private byteCount = 0
  private lastId = 0
  private turnId: string | null = null
  private terminal = false
  private current: { id?: string, event?: string, data?: string } = {}

  push(chunk: Uint8Array): AssistantPublicEvent[] {
    if (this.terminal) throw new AssistantSseError('data_after_terminal')
    let text: string
    try {
      text = this.decoder.decode(chunk, { stream: true })
    }
    catch {
      throw new AssistantSseError('invalid_utf8')
    }
    this.residual += text
    if (new TextEncoder().encode(this.residual).length > ASSISTANT_MAX_RESIDUAL_BYTES) {
      throw new AssistantSseError('residual_overflow')
    }
    const events: AssistantPublicEvent[] = []
    const parts = this.residual.split(/\r?\n/)
    this.residual = parts.pop() ?? ''
    for (const line of parts) {
      const parsed = this.pushLine(line)
      if (parsed) events.push(parsed)
    }
    return events
  }

  finish(): AssistantPublicEvent[] {
    if (this.residual.length > 0) throw new AssistantSseError('truncated_event')
    try {
      this.decoder.decode(new Uint8Array())
    }
    catch {
      throw new AssistantSseError('invalid_utf8')
    }
    if (!this.terminal) throw new AssistantSseError('missing_terminal')
    return []
  }

  private pushLine(line: string): AssistantPublicEvent | null {
    if (line === '') {
      if (!this.current.event && !this.current.data && !this.current.id) return null
      const event = this.flushEvent()
      this.current = {}
      return event
    }
    if (line.startsWith(':')) return null
    const idx = line.indexOf(':')
    const field = idx === -1 ? line : line.slice(0, idx)
    let value = idx === -1 ? '' : line.slice(idx + 1)
    if (value.startsWith(' ')) value = value.slice(1)
    if (field === 'id') this.current.id = value
    else if (field === 'event') this.current.event = value
    else if (field === 'data') this.current.data = (this.current.data ?? '') + value
    return null
  }

  private flushEvent(): AssistantPublicEvent {
    if (this.terminal) throw new AssistantSseError('data_after_terminal')
    const name = this.current.event ?? ''
    const rawId = this.current.id ?? ''
    const dataLine = this.current.data ?? ''
    const eventBytes = new TextEncoder().encode(dataLine).length
    if (eventBytes > ASSISTANT_MAX_EVENT_BYTES) throw new AssistantSseError('event_overflow')
    this.eventCount += 1
    this.byteCount += eventBytes
    if (this.eventCount > ASSISTANT_MAX_EVENTS) throw new AssistantSseError('event_limit')
    if (this.byteCount > ASSISTANT_MAX_TURN_BYTES) throw new AssistantSseError('turn_overflow')
    if (!/^[1-9][0-9]*$/.test(rawId)) throw new AssistantSseError('invalid_id')
    const sseId = Number(rawId)
    if (sseId <= this.lastId) throw new AssistantSseError('id_rewind')
    if (!(STAGES.has(name) || TERMINALS.has(name))) throw new AssistantSseError('unknown_event')
    let payload: Record<string, unknown>
    try {
      payload = JSON.parse(dataLine) as Record<string, unknown>
    }
    catch {
      throw new AssistantSseError('invalid_json')
    }
    if (payload.idempotent !== undefined) throw new AssistantSseError('internal_field')
    const allowed = STAGES.has(name) ? STAGE_FIELDS : name === 'answer' ? ANSWER_FIELDS : REFUSAL_FIELDS
    for (const key of Object.keys(payload)) {
      if (!allowed.has(key)) throw new AssistantSseError('unknown_field')
    }
    if (payload.event_id !== sseId) throw new AssistantSseError('event_id_mismatch')
    if (typeof payload.turn_id !== 'string' || payload.turn_id.length < 1) {
      throw new AssistantSseError('invalid_turn')
    }
    if (this.turnId === null) this.turnId = payload.turn_id
    else if (this.turnId !== payload.turn_id) throw new AssistantSseError('turn_mismatch')
    this.lastId = sseId
    if (STAGES.has(name)) {
      if (payload.stage !== name) throw new AssistantSseError('stage_mismatch')
      return {
        event: name as AssistantStageEvent['event'],
        event_id: sseId,
        turn_id: payload.turn_id,
        stage: name as AssistantStageEvent['stage'],
      }
    }
    this.terminal = true
    if (payload.type !== name) throw new AssistantSseError('type_mismatch')
    if (typeof payload.code !== 'string' || typeof payload.message !== 'string') {
      throw new AssistantSseError('invalid_terminal')
    }
    const terminal: AssistantTerminalEvent = {
      event: name as AssistantTerminalEvent['event'],
      event_id: sseId,
      turn_id: payload.turn_id,
      type: name as AssistantTerminalEvent['type'],
      code: payload.code,
      message: payload.message,
    }
    if (name === 'answer') {
      terminal.answer = payload.answer as string
      terminal.citations = payload.citations
      terminal.sources = payload.sources
    }
    return terminal
  }
}
