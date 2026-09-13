import { describe, expect, it, vi } from 'vitest'

import {
  boundedPageOffset,
  canonicalPageQuery,
  fetchAllPages,
  maxPageFor,
  pageFromQuery,
  pageLink,
  paginatedApiPath,
  paginationWindow,
} from '../../utils/pagination'

describe('pagination utilities', () => {
  it('normalizes route page values into the supported range', () => {
    expect(pageFromQuery(undefined, 20)).toBe(1)
    expect(pageFromQuery(['3', 'ignored'], 20)).toBe(3)
    expect(pageFromQuery('0', 20)).toBe(1)
    expect(pageFromQuery('2.5', 20)).toBe(1)
    expect(pageFromQuery('999999', 20)).toBe(5001)
    expect(pageFromQuery('999999', 12)).toBe(8334)
    expect(canonicalPageQuery('1', 20)).toBeUndefined()
    expect(canonicalPageQuery('999999', 12)).toBe('8334')
  })

  it('derives the last reachable page and offset from each endpoint page size', () => {
    expect(maxPageFor(20)).toBe(5001)
    expect(boundedPageOffset(5001, 20)).toBe(100_000)
    expect(maxPageFor(12)).toBe(8334)
    expect(boundedPageOffset(8334, 12)).toBe(99_996)
    expect(boundedPageOffset(999_999, 12)).toBe(99_996)
  })

  it('builds bounded API paths and preserves filters', () => {
    expect(paginatedApiPath('/articles', 2, 12, { category: 'engineering' }))
      .toBe('/articles?category=engineering&limit=13&offset=12')
    expect(paginatedApiPath('/articles', 999_999, 12))
      .toBe('/articles?limit=13&offset=99996')
  })

  it('returns visible items and next-page state from a lookahead row', () => {
    expect(paginationWindow([1, 2, 3], 2)).toEqual({ items: [1, 2], hasNext: true })
    expect(paginationWindow([1, 2], 2)).toEqual({ items: [1, 2], hasNext: false })
  })

  it('builds route links without exposing page one in the URL', () => {
    expect(pageLink('/search', 1, { q: 'sqlite' })).toEqual({
      path: '/search',
      query: { q: 'sqlite' },
    })
    expect(pageLink('/search', 2, { q: 'sqlite' })).toEqual({
      path: '/search',
      query: { q: 'sqlite', page: '2' },
    })
  })

  it('reads complete consumers in bounded batches', async () => {
    const request = vi.fn(async (limit: number, offset: number) =>
      [1, 2, 3, 4, 5].slice(offset, offset + limit),
    )

    await expect(fetchAllPages(request, 2)).resolves.toEqual([1, 2, 3, 4, 5])
    expect(request.mock.calls).toEqual([[2, 0], [2, 2], [2, 4]])
  })
})
