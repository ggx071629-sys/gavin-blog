import { absoluteSiteUrl, normalizeSiteUrl } from '../../utils/site'

export { normalizeSiteUrl }

export interface FeedEntry {
  path: string
  title: string
  description: string
  publishedAt: string
  updatedAt: string
}

export interface SitemapEntry {
  path: string
  updatedAt?: string
}

const escapeXml = (value: string): string => value
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&apos;')

const isoDate = (value: string): string => new Date(value).toISOString()

export const buildRssFeed = (siteUrl: string, entries: readonly FeedEntry[]): string => {
  const baseUrl = normalizeSiteUrl(siteUrl)
  const feedUrl = absoluteSiteUrl(baseUrl, '/rss.xml')
  const updatedAt = entries.length
    ? [...entries].sort((left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt))[0]!.updatedAt
    : new Date(0).toISOString()
  const items = [...entries]
    .sort((left, right) => Date.parse(right.publishedAt) - Date.parse(left.publishedAt))
    .map((entry) => {
      const url = escapeXml(absoluteSiteUrl(baseUrl, entry.path))
      return [
        '    <item>',
        `      <title>${escapeXml(entry.title)}</title>`,
        `      <link>${url}</link>`,
        `      <guid isPermaLink="true">${url}</guid>`,
        `      <description>${escapeXml(entry.description)}</description>`,
        `      <pubDate>${new Date(entry.publishedAt).toUTCString()}</pubDate>`,
        `      <atom:updated>${isoDate(entry.updatedAt)}</atom:updated>`,
        '    </item>',
      ].join('\n')
    })
    .join('\n')

  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
    '  <channel>',
    '    <title>Gavin · 技术与思考</title>',
    `    <link>${escapeXml(baseUrl)}</link>`,
    '    <description>Gavin 的技术文章、问题排查与项目复盘。</description>',
    '    <language>zh-CN</language>',
    `    <atom:link href="${escapeXml(feedUrl)}" rel="self" type="application/rss+xml"/>`,
    `    <lastBuildDate>${new Date(updatedAt).toUTCString()}</lastBuildDate>`,
    items,
    '  </channel>',
    '</rss>',
    '',
  ].filter(line => line !== '').join('\n') + '\n'
}

export const buildSitemap = (siteUrl: string, entries: readonly SitemapEntry[]): string => {
  const baseUrl = normalizeSiteUrl(siteUrl)
  const uniqueEntries = new Map<string, SitemapEntry>()
  for (const entry of entries) {
    uniqueEntries.set(absoluteSiteUrl(baseUrl, entry.path), entry)
  }
  const urls = [...uniqueEntries]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([url, entry]) => [
      '  <url>',
      `    <loc>${escapeXml(url)}</loc>`,
      ...(entry.updatedAt ? [`    <lastmod>${isoDate(entry.updatedAt)}</lastmod>`] : []),
      '  </url>',
    ].join('\n'))
    .join('\n')

  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    urls,
    '</urlset>',
    '',
  ].join('\n')
}

