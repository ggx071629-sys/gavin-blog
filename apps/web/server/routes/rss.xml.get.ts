import type { PublicArticle } from '~/types/api'
import { serverApiBase } from '~/utils/api-url'
import { articleDescription } from '~/utils/markdown'
import { buildRssFeed } from '../utils/discovery'

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const articles = await $fetch<PublicArticle[]>('/articles?limit=50&offset=0', {
    baseURL: serverApiBase(config.apiUpstream),
  })

  setResponseHeader(event, 'content-type', 'application/rss+xml; charset=utf-8')
  setResponseHeader(event, 'cache-control', 'public, max-age=300, stale-while-revalidate=3600')
  return buildRssFeed(config.public.siteUrl, articles.map(article => ({
    path: article.public_path,
    title: article.title,
    description: articleDescription(article.summary, article.content),
    publishedAt: article.published_at,
    updatedAt: article.updated_at,
  })))
})
