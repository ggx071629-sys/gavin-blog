import { afterEach, describe, expect, it, vi } from 'vitest'
import { isAssistantUiEnabled } from '../../utils/assistant/flag'
import { sameOriginApiBase } from '../../utils/assistant/origin'
import { isAssistantLauncherPath, isNavigableSourcePath } from '../../utils/assistant/allowlist'
import {
  ASSISTANT_MAX_EVENTS,
  AssistantSseError,
  AssistantSseParser,
} from '../../utils/assistant/sse'
import { splitSseForTest } from '../helpers/assistant-sse'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { closeAnswerCitations, splitAnswerMarkers } from '../../utils/assistant/citations'
import { mapAssistantCode, parseRetryAfter } from '../../utils/assistant/errors'
import {
  COUNT_POINTS,
  emptyAssistantMemory,
} from '../../utils/assistant/persistence'
import { assertResponseUrl, parseSessionStatus } from '../../utils/assistant/client'
import { AssistantGenerationFence } from '../../utils/assistant/generation'
import {
  ASSISTANT_POLL_HORIZON_MS,
  nextPollingDelay,
  pollingHorizonExpired,
} from '../../utils/assistant/polling'

const stage = (id: number, name: string, turn = 'turn-1') =>
  `id: ${id}\nevent: ${name}\ndata: ${JSON.stringify({ event_id: id, turn_id: turn, stage: name })}\n\n`

const terminal = (id: number, turn = 'turn-1') =>
  `id: ${id}\nevent: answer\ndata: ${JSON.stringify({
    event_id: id,
    turn_id: turn,
    type: 'answer',
    code: 'answered',
    message: 'ok',
    answer: '正文[1]',
    citations: [{ n: '1', title: 'Python notes', path: '/notes/2026/08/python-notes' }],
    sources: [{ n: '1', title: 'Python notes', path: '/notes/2026/08/python-notes' }],
  })}\n\n`

describe('assistant UI flag', () => {
  it('is strict true only', () => {
    expect(isAssistantUiEnabled(true)).toBe(true)
    expect(isAssistantUiEnabled('true')).toBe(true)
    expect(isAssistantUiEnabled('TRUE')).toBe(false)
    expect(isAssistantUiEnabled('1')).toBe(false)
    expect(isAssistantUiEnabled('')).toBe(false)
    expect(isAssistantUiEnabled(undefined)).toBe(false)
    expect(isAssistantUiEnabled(null)).toBe(false)
  })
})

describe('assistant origin', () => {
  it('accepts only same-origin relative /api/v1', () => {
    expect(sameOriginApiBase('/api/v1', 'http://127.0.0.1:3000')).toBe(true)
    expect(sameOriginApiBase('https://evil.test/api/v1', 'http://127.0.0.1:3000')).toBe(false)
    expect(sameOriginApiBase('/api/v2', 'http://127.0.0.1:3000')).toBe(false)
    expect(sameOriginApiBase('//evil.test/api/v1', 'http://127.0.0.1:3000')).toBe(false)
  })

  it('requires the exact final endpoint without redirects, suffixes, queries, or hashes', () => {
    const response = new Response('{}')
    const withUrl = (url: string) => Object.defineProperty(response, 'url', { value: url, configurable: true })
    withUrl('https://site.test/api/v1/assistant/session')
    expect(() => assertResponseUrl(response, '/api/v1/assistant/session', 'https://site.test')).not.toThrow()
    for (const url of [
      'https://site.test/prefix/api/v1/assistant/session',
      'https://site.test/api/v1/assistant/session/extra',
      'https://site.test/api/v1//assistant/session',
      'https://site.test/api/v1/assistant/session?next=1',
      'https://evil.test/api/v1/assistant/session',
    ]) {
      withUrl(url)
      expect(() => assertResponseUrl(response, '/api/v1/assistant/session', 'https://site.test')).toThrow(/origin_rejected/)
    }
  })
})

describe('assistant allowlist', () => {
  it('matches launcher paths without query or hash', () => {
    expect(isAssistantLauncherPath('/')).toBe(true)
    expect(isAssistantLauncherPath('/articles')).toBe(true)
    expect(isAssistantLauncherPath('/notes/2026/08/python-notes')).toBe(true)
    expect(isAssistantLauncherPath('/projects/my-blog')).toBe(true)
    expect(isAssistantLauncherPath('/admin')).toBe(false)
    expect(isAssistantLauncherPath('/articles?x=1')).toBe(false)
    expect(isAssistantLauncherPath('/notes/2026/13/python-notes')).toBe(false)
    expect(isAssistantLauncherPath('/notes/2026/08/-bad')).toBe(false)
  })

  it('accepts only navigable source paths', () => {
    expect(isNavigableSourcePath('/')).toBe(true)
    expect(isNavigableSourcePath('/notes/2026/08/python-notes')).toBe(true)
    expect(isNavigableSourcePath('/projects/my-blog')).toBe(true)
    expect(isNavigableSourcePath('/books/2026/08/sample')).toBe(true)
    expect(isNavigableSourcePath('/articles')).toBe(false)
    expect(isNavigableSourcePath('https://evil.test/notes/2026/08/python-notes')).toBe(false)
    expect(isNavigableSourcePath('/notes/2026/08/python-notes?x=1')).toBe(false)
  })
})

describe('assistant SSE parser', () => {
  it('parses events across arbitrary chunk and CRLF boundaries', () => {
    const parser = new AssistantSseParser()
    const payload = `${stage(1, 'checking')}${stage(2, 'retrieving')}${terminal(3)}`.replaceAll('\n', '\r\n')
    const events = []
    for (const chunk of splitSseForTest(payload, [1, 3, 7, 11])) {
      events.push(...parser.push(chunk))
    }
    parser.finish()
    expect(events.map(item => item.event)).toEqual(['checking', 'retrieving', 'answer'])
  })

  it('rejects fatal UTF-8, unknown fields, and internal idempotent', () => {
    const parser = new AssistantSseParser()
    expect(() => parser.push(new Uint8Array([0xff, 0xfe]))).toThrow(AssistantSseError)
    const bad = new AssistantSseParser()
    expect(() => {
      bad.push(new TextEncoder().encode(
        'id: 1\nevent: checking\ndata: {"event_id":1,"turn_id":"t","stage":"checking","idempotent":1}\n\n',
      ))
    }).toThrow(/internal_field/)
  })

  it('enforces the 16-event logical-turn cap across reconnects', () => {
    const parser = new AssistantSseParser()
    for (let index = 1; index <= ASSISTANT_MAX_EVENTS - 1; index += 1) {
      parser.push(new TextEncoder().encode(stage(index, 'checking')))
    }
    expect(() => {
      parser.push(new TextEncoder().encode(`${stage(16, 'checking')}${stage(17, 'retrieving')}`))
    }).toThrow(/event_limit/)
  })

  it('rejects rewind ids, missing terminal EOF, and data after terminal', () => {
    const parser = new AssistantSseParser()
    parser.push(new TextEncoder().encode(stage(2, 'checking')))
    expect(() => parser.push(new TextEncoder().encode(stage(1, 'retrieving')))).toThrow(/id_rewind/)
    const eof = new AssistantSseParser()
    eof.push(new TextEncoder().encode(stage(1, 'checking')))
    expect(() => eof.finish()).toThrow(/missing_terminal/)
  })

  it('keeps the Host reconnect path on one parser instance', () => {
    const source = readFileSync(resolve(process.cwd(), 'components/AssistantHost.vue'), 'utf8')
    const runStream = source.slice(source.indexOf('const runStream'), source.indexOf('const startPolling'))
    expect(runStream).not.toMatch(/new AssistantSseParser/)
    expect(source).toMatch(/new AssistantSseParser\(\)/)
  })
})

describe('assistant citations', () => {
  it('keeps array subscripts literal while closing terminal citations', () => {
    const answer = '读取 `a[99]` 和 `items [ 1 ][2]`。[3]'
    expect(splitAnswerMarkers(answer)).toEqual([
      { text: '读取 a[99] 和 items [ 1 ][2]。' },
      { marker: '3' },
    ])
    expect(splitAnswerMarkers('`a[99]`[3]')).toEqual([
      { text: 'a[99]' }, { marker: '3' },
    ])
    expect(splitAnswerMarkers('legacy[3]')).toEqual([
      { text: 'legacy' }, { marker: '3' },
    ])
    const source = { n: '3', title: 'Arrays', path: '/projects/arrays' }
    const closed = closeAnswerCitations(answer, [source], [source])
    expect(closed?.markers.map(item => item.n)).toEqual(['3'])
    expect(closeAnswerCitations('读取 `a[99]`。[4]', [source], [source])).toBeNull()
  })
  it('splits each [n] marker once without duplicating the preceding text', () => {
    expect(splitAnswerMarkers('站点用 FastAPI。[1]')).toEqual([
      { text: '站点用 FastAPI。' },
      { marker: '1' },
    ])
    expect(splitAnswerMarkers('[1]开头和结尾[2]')).toEqual([
      { marker: '1' },
      { text: '开头和结尾' },
      { marker: '2' },
    ])
  })

  it('closes markers only to matching citations and allowlisted sources', () => {
    const closed = closeAnswerCitations(
      '站点用 FastAPI。[1]',
      [{ n: '1', title: 'Python notes', path: '/notes/2026/08/python-notes' }],
      [{ n: '1', title: 'Python notes', path: '/notes/2026/08/python-notes' }],
    )
    expect(closed?.sources[0]?.path).toBe('/notes/2026/08/python-notes')
    expect(closeAnswerCitations('见[2]', [{ n: '1', title: 'Python notes', path: '/notes/2026/08/python-notes' }], [])).toBeNull()
    expect(closeAnswerCitations(
      '见[1]',
      [{ n: '1', title: 'Python notes', path: '/notes/2026/08/python-notes' }],
      [{ n: '1', title: 'Python notes', path: 'https://evil.test' }],
    )).toBeNull()
    expect(closeAnswerCitations(
      '见[1]',
      [{ n: '1', title: 'Python notes', path: '/notes/2026/08/python-notes', injected: true }],
      [{ n: '1', title: 'Python notes', path: '/notes/2026/08/python-notes' }],
    )).toBeNull()
  })

  it('closes multiple chunk markers against a deduplicated article source', () => {
    const source = { n: '1', title: 'SSL', path: '/notes/2026/08/ssl' }
    const citations = [source, { ...source, n: '2', heading_path: 'Renewal' }]
    const closed = closeAnswerCitations('Certbot[1]. Renewal[2]', citations, [source])
    expect(closed?.markers.map(marker => marker.n)).toEqual(['1', '2'])
    expect(closed?.sources).toHaveLength(1)
    expect(closeAnswerCitations('Unknown[3]', citations, [source])).toBeNull()
    expect(closeAnswerCitations('Forged[2]', [source, { ...citations[1], path: '/about' }], [source])).toBeNull()
    expect(closeAnswerCitations('Forged[2]', citations, [{ ...source, n: '3' }])).toBeNull()
  })
})

describe('assistant document controller barriers', () => {
  afterEach(() => vi.useRealTimers())

  it('aborts every old request and rejects a delayed completion after DELETE generation advances', async () => {
    const fence = new AssistantGenerationFence()
    const request = fence.controller()
    const captured = fence.value
    let release!: (value: string) => void
    const delayed = new Promise<string>((resolve) => { release = resolve })
    const writes: string[] = []
    const completion = delayed.then((value) => {
      if (fence.isCurrent(captured)) writes.push(value)
    })
    fence.advance()
    expect(request.signal.aborted).toBe(true)
    release('late body')
    await completion
    expect(writes).toEqual([])
  })

  it('uses a controlled 3-second poll clock, bounded Retry-After, and one 180-second horizon', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-08-29T00:00:00Z'))
    const startedAt = Date.now()
    expect(nextPollingDelay(200, true, null)).toBe(3000)
    expect(nextPollingDelay(200, false, '30')).toBeNull()
    expect(nextPollingDelay(429, true, '7')).toBe(7000)
    expect(nextPollingDelay(503, true, '0')).toBeNull()
    vi.advanceTimersByTime(ASSISTANT_POLL_HORIZON_MS - 1)
    expect(pollingHorizonExpired(startedAt, Date.now())).toBe(false)
    vi.advanceTimersByTime(1)
    expect(pollingHorizonExpired(startedAt, Date.now())).toBe(true)
  })

  it('closes hydrated answers before allowing source paths into Vue state', () => {
    const base = {
      session_id: 's1',
      created_at: '2026-08-29T00:00:00Z',
      idle_expires_at: '2026-08-29T00:30:00Z',
      absolute_expires_at: '2026-08-30T00:00:00Z',
      policy: {
        question_max_chars: 500,
        session_idle_seconds: 1800,
        session_absolute_seconds: 86400,
        body_retention_seconds: 900,
      },
      active_turn: null,
    }
    const validTurn = {
      turn_id: 't1', created_at: base.created_at, status: 'answer', code: 'answered',
      message: 'ok', question: 'q', answer: 'a[1]', body_available: true,
      citations: [{ n: '1', title: 'Note', path: '/notes/2026/08/note' }],
      sources: [{ n: '1', title: 'Note', path: '/notes/2026/08/note' }],
    }
    expect(parseSessionStatus({ ...base, turns: [validTurn] }).turns[0]?.answer).toBe('a[1]')
    expect(parseSessionStatus({ ...base, turns: [{ ...validTurn, feedback: 'helpful' }] }).turns[0]?.feedback).toBe('helpful')
    expect(() => parseSessionStatus({ ...base, turns: [{ ...validTurn, feedback: 'raw text' }] })).toThrow(/invalid_request/)
    expect(() => parseSessionStatus({ ...base, turns: [{ ...validTurn, body_available: false, feedback: 'helpful' }] })).toThrow(/invalid_request/)
    const multi = { ...validTurn, answer: 'a[1][2]', citations: [...validTurn.citations, { ...validTurn.citations[0], n: '2' }] }
    const restored = parseSessionStatus({ ...base, turns: [multi] }).turns[0]
    expect(restored?.answer).toBe('a[1][2]')
    expect(restored?.citations).toHaveLength(2)
    const forged = parseSessionStatus({
      ...base,
      turns: [{ ...validTurn, sources: [{ n: '1', title: 'Note', path: 'https://evil.test' }] }],
    })
    expect(forged.turns[0]?.answer).toBeNull()
    expect(forged.turns[0]?.sources).toBeNull()
    expect(() => parseSessionStatus({ ...base, turns: [], injected: true })).toThrow(/invalid_request/)
  })

  it('keeps raw fields out of restorable form controls and wires lifecycle invalidation', () => {
    const panel = readFileSync(resolve(process.cwd(), 'components/AssistantPanel.vue'), 'utf8')
    const host = readFileSync(resolve(process.cwd(), 'components/AssistantHost.vue'), 'utf8')
    expect(panel).toMatch(/autocomplete="off"/)
    expect(panel).not.toMatch(/name="ask-gavin/)
    expect(host).toMatch(/generation\.advance\(\)/)
    expect(host).toMatch(/pagehide/)
    expect(host).toMatch(/pageshow/)
    expect(host).toMatch(/stopPolling\(\)/)
  })
})

describe('assistant errors and persistence', () => {
  afterEach(() => {
    localStorage.clear()
    sessionStorage.clear()
  })

  it('maps machine codes and Retry-After bounds', () => {
    expect(mapAssistantCode('insufficient_evidence').title).toContain('证据不足')
    expect(mapAssistantCode('provider_result_unknown').action).toBe('refresh')
    expect(mapAssistantCode('output_invalid').title).toBe('回答格式校验失败')
    expect(mapAssistantCode('output_rejected').title).toBe('回答未通过证据校验')
    expect(mapAssistantCode('output_rejected').action).toBeUndefined()
    expect(mapAssistantCode('csrf_failed').action).toBe('resync')
    expect(mapAssistantCode('origin_rejected').action).toBeUndefined()
    expect(parseRetryAfter('30')).toBe(30)
    expect(parseRetryAfter('0')).toBeNull()
    expect(parseRetryAfter('86401')).toBeNull()
    expect(parseRetryAfter('1.5')).toBeNull()
  })

  it('distinguishes input budget rejection from an unconfirmed answer', () => {
    const input = mapAssistantCode('input_budget_exceeded')
    expect(input.title).toBe('回答所需内容超出输入限制')
    expect(input.body).toContain('已停止后续模型调用')
    expect(input.action).toBeUndefined()
    const unknown = mapAssistantCode('provider_result_unknown')
    expect(unknown.title).toBe('回答状态未确认')
    expect(unknown.body).toContain('不会重新发送问题')
    expect(unknown.action).toBe('refresh')
  })

  it('counts unicode code points and initializes empty memory', () => {
    expect(COUNT_POINTS('你好a')).toBe(3)
    expect(emptyAssistantMemory().idempotencyKey).toBeNull()
  })
})
