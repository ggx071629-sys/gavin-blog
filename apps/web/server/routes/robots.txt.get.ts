import { absoluteSiteUrl, normalizeSiteUrl } from '~/utils/site'

export default defineEventHandler((event) => {
  const config = useRuntimeConfig()
  const siteUrl = normalizeSiteUrl(config.public.siteUrl)
  setResponseHeader(event, 'content-type', 'text/plain; charset=utf-8')
  setResponseHeader(event, 'cache-control', 'public, max-age=3600')
  return [
    'User-agent: *',
    'Allow: /',
    'Disallow: /admin/',
    '',
    `Sitemap: ${absoluteSiteUrl(siteUrl, '/sitemap.xml')}`,
    '',
  ].join('\n')
})

