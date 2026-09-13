import { absoluteSiteUrl } from '~/utils/site'

type JsonLd = Record<string, unknown> | Record<string, unknown>[]

export interface SiteSeoOptions {
  title: string
  description: string
  canonicalPath?: string
  ogType?: 'website' | 'article'
  indexable?: boolean
  publishedTime?: string
  modifiedTime?: string
  tags?: string[]
  imagePath?: string
  jsonLd?: JsonLd
}

export const useSiteSeo = (resolve: () => SiteSeoOptions) => {
  const config = useRuntimeConfig()
  const route = useRoute()
  const options = computed(resolve)
  const canonical = computed(() => absoluteSiteUrl(
    config.public.siteUrl,
    options.value.canonicalPath || route.path,
  ))
  const socialImage = computed(() => absoluteSiteUrl(
    config.public.siteUrl,
    options.value.imagePath || '/og/gavin-notes-default.png',
  ))

  useSeoMeta({
    title: () => options.value.title,
    description: () => options.value.description,
    robots: () => options.value.indexable === false ? 'noindex,follow' : 'index,follow',
    ogTitle: () => options.value.title,
    ogDescription: () => options.value.description,
    ogType: () => options.value.ogType || 'website',
    ogUrl: canonical,
    ogSiteName: 'Gavin',
    ogLocale: 'zh_CN',
    ogImage: socialImage,
    ogImageWidth: 1200,
    ogImageHeight: 630,
    ogImageAlt: 'Gavin / Notes on Building — Independent Engineering Journal',
    twitterCard: 'summary_large_image',
    twitterTitle: () => options.value.title,
    twitterDescription: () => options.value.description,
    twitterImage: socialImage,
    articlePublishedTime: () => options.value.publishedTime,
    articleModifiedTime: () => options.value.modifiedTime,
    articleTag: () => options.value.tags,
  })

  useHead(() => ({
    link: [
      { rel: 'canonical', href: canonical.value },
      { rel: 'alternate', type: 'application/rss+xml', title: 'Gavin RSS', href: absoluteSiteUrl(config.public.siteUrl, '/rss.xml') },
    ],
    script: options.value.jsonLd
      ? [{
          key: 'gavin-json-ld',
          type: 'application/ld+json',
          textContent: JSON.stringify(options.value.jsonLd).replaceAll('<', '\\u003c'),
        }]
      : [],
  }))
}
