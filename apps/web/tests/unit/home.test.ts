import { describe, expect, it, vi } from 'vitest'
import type { PublicArticle, PublicTaxonomy } from '../../types/api'
import { loadHomeContent } from '../../utils/home'

const article = (id: number) => ({ id, title: `Article ${id}`, summary: '', content: 'large private-to-render payload', published_at: '2026-09-01T00:00:00Z', public_path: `/notes/2026/09/article-${id}` }) as PublicArticle
const taxonomy = (ids: number[], total = 200): PublicTaxonomy => ({
  categories: ids.map(id => ({ id, name: `Category ${id}`, slug: `category-${id}`, article_count: 10 })), tags: [], total_article_count: total,
})

describe('homepage content', () => {
  it('bounds category requests by stable id and strips full bodies from the page payload', async () => {
    const fetcher = vi.fn(async (path: string) => path === '/taxonomy' ? taxonomy([8, 3, 6, 1, 4]) : [article(7)])
    const result = await loadHomeContent(fetcher as never)
    expect(result.topics.map(topic => topic.category.id)).toEqual([1, 3, 4])
    expect(result.total).toBe(200)
    expect(result.categoryCount).toBe(5)
    expect(fetcher.mock.calls.map(([path]) => path)).toEqual([
      '/articles?limit=4&offset=0', '/taxonomy',
      '/articles?category=category-1&limit=1&offset=0', '/articles?category=category-3&limit=1&offset=0', '/articles?category=category-4&limit=1&offset=0',
    ])
    expect(result.topics[0]?.article?.public_path).toBe('/notes/2026/09/article-7')
    expect(JSON.stringify(result)).not.toContain('large private-to-render payload')
    expect(result.articles[0]).not.toHaveProperty('content')
  })

  it('reuses recent articles when there are no current categories and keeps the site total', async () => {
    const fetcher = vi.fn(async (path: string) => path === '/taxonomy' ? taxonomy([], 9) : [article(9)])
    const result = await loadHomeContent(fetcher as never)
    expect(result.topics).toEqual([])
    expect(result.articles[0]?.id).toBe(9)
    expect(result.total).toBe(9)
    expect(fetcher).toHaveBeenCalledTimes(2)
    expect(fetcher.mock.calls.flat().join()).not.toContain('uncategorized')
  })

  it('distinguishes empty content, taxonomy failure and individual topic failure', async () => {
    const empty = await loadHomeContent((async (path: string) => path === '/taxonomy' ? taxonomy([], 0) : []) as never)
    expect(empty.total).toBe(0)
    expect(empty.taxonomyFailed).toBe(false)
    const degraded = await loadHomeContent((async (path: string) => {
      if (path === '/taxonomy') throw new Error('unavailable')
      return [article(1)]
    }) as never)
    expect(degraded.total).toBeNull()
    expect(degraded.taxonomyFailed).toBe(true)
    expect(degraded.articles).toHaveLength(1)
    const partial = await loadHomeContent((async (path: string) => {
      if (path === '/taxonomy') return taxonomy([1, 2])
      if (path.includes('category-1')) throw new Error('unavailable')
      if (path.includes('category-2')) return []
      return [article(1)]
    }) as never)
    expect(partial.topics.map(topic => topic.state)).toEqual(['error', 'empty'])
    expect(partial.topics.every(topic => topic.article === null)).toBe(true)
  })

  it('propagates primary article and aborted request failures instead of inventing an empty success', async () => {
    await expect(loadHomeContent((async () => { throw new Error('503') }) as never)).rejects.toThrow('503')
    const signal = AbortSignal.abort()
    await expect(loadHomeContent((async (path: string) => {
      if (path === '/taxonomy') throw new DOMException('Aborted', 'AbortError')
      return [article(1)]
    }) as never, signal)).rejects.toThrow('Aborted')
  })
})
