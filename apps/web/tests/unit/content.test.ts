import { describe, expect, it } from 'vitest'

import { archiveDayStamp, bookLedgerMonth, ratingLabel, readingStatusLabel } from '../../utils/content'
import { readingMinutesFromContent } from '../../utils/readingTime'

describe('extended content utilities', () => {
  it('renders localized reading states', () => {
    expect(readingStatusLabel('planned')).toBe('想读')
    expect(readingStatusLabel('reading')).toBe('在读')
    expect(readingStatusLabel('completed')).toBe('读完')
    expect(readingStatusLabel('paused')).toBe('暂停')
  })

  it('renders optional ratings accessibly', () => {
    expect(ratingLabel(4)).toBe('4 / 5 分')
    expect(ratingLabel(null)).toBe('暂未评分')
  })

  it('formats book ledger months from reading_date or published_at', () => {
    expect(bookLedgerMonth('2026-08-08', '2025-01-01T00:00:00Z')).toBe('2026.08')
    expect(bookLedgerMonth(null, '2025-11-02T12:00:00Z')).toBe('2025.11')
  })

  it('formats archive dates as UTC MM.DD', () => {
    expect(archiveDayStamp('2026-08-14T00:00:00Z')).toBe('08.14')
    expect(archiveDayStamp('2026-01-02T23:00:00Z')).toBe('01.02')
  })
})

describe('reading minutes', () => {
  it('uses ceil(length / 500) with a floor of 1', () => {
    expect(readingMinutesFromContent('')).toBe(1)
    expect(readingMinutesFromContent('a'.repeat(500))).toBe(1)
    expect(readingMinutesFromContent('a'.repeat(501))).toBe(2)
  })
})
