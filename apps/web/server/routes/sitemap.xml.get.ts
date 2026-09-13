import type { PublicArticle, PublicBookNote, PublicProject } from '~/types/api'
import { fetchAllPages } from '~/utils/pagination'
import { serverApiBase } from '~/utils/api-url'
import { buildSitemap, type SitemapEntry } from '../utils/discovery'

const staticEntries: SitemapEntry[] = [
  { path: '/' },
  { path: '/about' },
  { path: '/archive' },
  { path: '/articles' },
  { path: '/books' },
  { path: '/projects' },
]

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig()
  const request = <T>(path: string) => $fetch<T>(path, { baseURL: serverApiBase(config.apiUpstream) })
  const requestAll = <T>(path: string) => fetchAllPages<T>((limit, offset) =>
    request<T[]>(`${path}?limit=${limit}&offset=${offset}`),
  )
  const [articles, projects, books] = await Promise.all([
    requestAll<PublicArticle>('/articles'),
    requestAll<PublicProject>('/projects'),
    requestAll<PublicBookNote>('/books'),
  ])
  const contentEntries: SitemapEntry[] = [
    ...articles.map(item => ({ path: item.public_path, updatedAt: item.updated_at })),
    ...projects.map(item => ({ path: item.public_path, updatedAt: item.updated_at })),
    ...books.map(item => ({ path: item.public_path, updatedAt: item.updated_at })),
  ]

  setResponseHeader(event, 'content-type', 'application/xml; charset=utf-8')
  setResponseHeader(event, 'cache-control', 'public, max-age=300, stale-while-revalidate=3600')
  return buildSitemap(config.public.siteUrl, [...staticEntries, ...contentEntries])
})
