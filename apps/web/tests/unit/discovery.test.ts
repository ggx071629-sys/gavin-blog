import { describe, expect, it } from 'vitest'
import { buildRssFeed, buildSitemap, normalizeSiteUrl } from '../../server/utils/discovery'

describe('discovery documents', () => {
  it('normalizes an absolute site URL', () => {
    expect(normalizeSiteUrl('https://gavin.example///')).toBe('https://gavin.example')
    expect(() => normalizeSiteUrl('/relative')).toThrow('absolute HTTP(S) URL')
  })

  it('builds escaped RSS with stable absolute article links', () => {
    const xml = buildRssFeed('https://gavin.example/', [{
      path: '/notes/2026/08/a&b',
      title: 'A & <B>',
      description: 'Use "safe" XML',
      publishedAt: '2026-08-01T08:00:00Z',
      updatedAt: '2026-08-02T08:00:00Z',
    }])

    expect(xml).toContain('<title>A &amp; &lt;B&gt;</title>')
    expect(xml).toContain('https://gavin.example/notes/2026/08/a&amp;b')
    expect(xml).toContain('<atom:updated>2026-08-02T08:00:00.000Z</atom:updated>')
  })

  it('deduplicates and sorts sitemap entries', () => {
    const xml = buildSitemap('https://gavin.example', [
      { path: '/projects/zeta', updatedAt: '2026-07-01T00:00:00Z' },
      { path: '/', updatedAt: '2026-08-01T00:00:00Z' },
      { path: '/projects/zeta', updatedAt: '2026-06-01T00:00:00Z' },
    ])

    expect(xml.match(/<url>/g)).toHaveLength(2)
    expect(xml.indexOf('https://gavin.example/</loc>')).toBeLessThan(xml.indexOf('/projects/zeta</loc>'))
  })
})
