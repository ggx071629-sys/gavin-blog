import { parseRetryAfter } from './errors'

export const ASSISTANT_POLL_INTERVAL_MS = 3_000
export const ASSISTANT_POLL_HORIZON_MS = 180_000

export function pollingHorizonExpired(startedAt: number, now: number) {
  return now - startedAt >= ASSISTANT_POLL_HORIZON_MS
}

export function nextPollingDelay(
  status: number,
  activeTurn: boolean,
  retryAfter: string | null,
): number | null {
  if (status === 200) return activeTurn ? ASSISTANT_POLL_INTERVAL_MS : null
  if (status !== 429 && status !== 503) return null
  const seconds = parseRetryAfter(retryAfter)
  return seconds === null ? null : seconds * 1000
}
