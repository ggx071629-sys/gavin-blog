export type AssistantMemory = {
  draft: string
  transcript: unknown[]
  idempotencyKey: string | null
  payload: unknown
  lastEventId: number | null
}

export function emptyAssistantMemory(): AssistantMemory {
  return {
    draft: '',
    transcript: [],
    idempotencyKey: null,
    payload: null,
    lastEventId: null,
  }
}

export const COUNT_POINTS = (value: string): number => [...value].length
