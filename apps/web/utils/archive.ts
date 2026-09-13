import type { PublicArticle } from '~/types/api'

export interface ArticleYearGroup {
  year: number
  articles: PublicArticle[]
}

export const groupArticlesByYear = (articles: readonly PublicArticle[]): ArticleYearGroup[] => {
  const sorted = [...articles].sort((left, right) =>
    Date.parse(right.published_at) - Date.parse(left.published_at),
  )
  const groups = new Map<number, PublicArticle[]>()

  for (const article of sorted) {
    const year = new Date(article.published_at).getUTCFullYear()
    const group = groups.get(year) || []
    group.push(article)
    groups.set(year, group)
  }

  return [...groups].map(([year, groupArticles]) => ({
    year,
    articles: groupArticles,
  }))
}

