export const normalizeSiteUrl = (value: string): string => {
  let url: URL
  try {
    url = new URL(value)
  }
  catch {
    throw new Error('siteUrl must be an absolute HTTP(S) URL')
  }

  if (!['http:', 'https:'].includes(url.protocol)) {
    throw new Error('siteUrl must be an absolute HTTP(S) URL')
  }

  url.hash = ''
  url.search = ''
  return url.toString().replace(/\/+$/, '')
}

export const absoluteSiteUrl = (siteUrl: string, path: string): string =>
  new URL(path.replace(/^\/+/, ''), `${normalizeSiteUrl(siteUrl)}/`).toString()

export const websiteSearchAction = (siteUrl: string) => ({
  '@type': 'SearchAction' as const,
  target: `${absoluteSiteUrl(siteUrl, '/search')}?q={search_term_string}`,
  'query-input': 'required name=search_term_string',
})
