import { describe, expect, it } from 'vitest'
import type { PublicArticle } from '../../types/api'
import { groupArticlesByYear } from '../../utils/archive'

const article = (id: number, publishedAt: string): PublicArticle => ({
  id,
  title: `Article ${id}`,
  slug: `article-${id}`,
  summary: '',
  content: '',
  published_at: publishedAt,
  updated_at: publishedAt,
  public_path: `/notes/2026/01/article-${id}`,
  category: null,
  tags: [],
  references: [],
  wikilinks: [],
})

describe('groupArticlesByYear', () => {
  it('sorts articles newest-first and groups years newest-first', () => {
    const input = [
      article(1, '2025-12-20T08:00:00Z'),
      article(2, '2026-01-02T08:00:00Z'),
      article(3, '2025-12-31T08:00:00Z'),
    ]

    expect(groupArticlesByYear(input).map(group => ({
      year: group.year,
      ids: group.articles.map(item => item.id),
    }))).toEqual([
      { year: 2026, ids: [2] },
      { year: 2025, ids: [3, 1] },
    ])
  })

  it('does not mutate the API response', () => {
    const input = [
      article(1, '2025-01-01T08:00:00Z'),
      article(2, '2026-01-01T08:00:00Z'),
    ]

    groupArticlesByYear(input)

    expect(input.map(item => item.id)).toEqual([1, 2])
  })
})
