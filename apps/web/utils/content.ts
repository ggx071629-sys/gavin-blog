export type ReadingStatus = 'planned' | 'reading' | 'completed' | 'paused'

const readingStatusLabels: Record<ReadingStatus, string> = {
  planned: '想读',
  reading: '在读',
  completed: '读完',
  paused: '暂停',
}

export function readingStatusLabel(status: ReadingStatus): string {
  return readingStatusLabels[status]
}

export function ratingLabel(rating: number | null): string {
  return rating === null ? '暂未评分' : `${rating} / 5 分`
}

export function bookLedgerMonth(readingDate: string | null, publishedAt: string): string {
  const iso = readingDate ? `${readingDate}T00:00:00Z` : publishedAt
  const date = new Date(iso)
  return `${date.getUTCFullYear()}.${String(date.getUTCMonth() + 1).padStart(2, '0')}`
}

export function archiveDayStamp(publishedAt: string): string {
  const date = new Date(publishedAt)
  return `${String(date.getUTCMonth() + 1).padStart(2, '0')}.${String(date.getUTCDate()).padStart(2, '0')}`
}
