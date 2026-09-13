import { readingMinutesFromContent } from './readingTime'
import type { PublicArticle, PublicTaxonomy, TaxonomyOption } from '~/types/api'

export type HomeArticle = Pick<PublicArticle, 'id' | 'title' | 'summary' | 'published_at' | 'public_path'> & { readingMinutes?: number; category?: PublicArticle['category']; tags?: PublicArticle['tags'] }
export interface HomeTopic {
  category: TaxonomyOption
  article: HomeArticle | null
  state: 'ready' | 'empty' | 'error'
}
export interface HomeContent {
  articles: HomeArticle[]
  topics: HomeTopic[]
  total: number | null
  categoryCount: number | null
  taxonomyFailed: boolean
}
type FetchHome = <T>(path: string) => Promise<T>

const summary = ({ id, title, summary, published_at, public_path, content, category, tags }: PublicArticle): HomeArticle =>
  ({ id, title, summary, published_at, public_path, readingMinutes: readingMinutesFromContent(content), category, tags })

export async function loadHomeContent(fetcher: FetchHome, signal?: AbortSignal): Promise<HomeContent> {
  // The API remains authoritative for published_at DESC, id DESC ordering.
  const [rows, taxonomy] = await Promise.all([
    fetcher<PublicArticle[]>('/articles?limit=4&offset=0'),
    fetcher<PublicTaxonomy>('/taxonomy').catch((error) => {
      if (signal?.aborted) throw error
      return null
    }),
  ])
  const categories = [...(taxonomy?.categories ?? [])]
    .filter(category => category.article_count > 0)
    .sort((a, b) => a.id - b.id)
  const topics = await Promise.all(categories.slice(0, 3).map(async (category): Promise<HomeTopic> => {
    try {
      const articles = await fetcher<PublicArticle[]>(`/articles?category=${encodeURIComponent(category.slug)}&limit=1&offset=0`)
      return { category, article: articles[0] ? summary(articles[0]) : null, state: articles.length ? 'ready' : 'empty' }
    }
    catch (error) {
      if (signal?.aborted) throw error
      return { category, article: null, state: 'error' }
    }
  }))
  return {
    articles: rows.slice(0, 4).map(summary), topics,
    total: taxonomy?.total_article_count ?? null,
    categoryCount: taxonomy ? categories.length : null,
    taxonomyFailed: taxonomy === null,
  }
}

export const homeDate = (value: string) => new Date(value).toISOString().slice(0, 10)
