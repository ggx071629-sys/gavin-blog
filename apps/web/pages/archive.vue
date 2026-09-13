<template>
  <section class="page-shell public-page archive-page max-w-4xl mx-auto space-y-6">
    <header class="archive-masthead space-y-4">
      <SectionHeading label="时间归档" />
      <div class="archive-hero-composition">
      <div class="archive-masthead-title space-y-3">
        <h1 class="ee-heading archive-masthead-heading font-black tracking-tight text-4xl sm:text-5xl text-[var(--ee-ink)]">按时间查看文章</h1>
        <p class="archive-masthead-note text-[var(--ee-ink-muted)] text-base leading-relaxed">
          所有已发布文章按年份和发布日期排列，方便回看以前写过的内容。
        </p>
      </div>
      <PageHeroArtwork kind="archive" />
      </div>
    </header>

    <div
      class="archive-results"
      data-testid="archive-results"
      :aria-busy="listBusy ? 'true' : 'false'"
    >
      <div v-if="groups.length" class="archive-spine">
        <section
          v-for="group in groups"
          :key="group.year"
          :aria-labelledby="`year-${group.year}`"
          class="archive-year"
        >
          <header class="archive-year-label">
            <h2 :id="`year-${group.year}`" class="ee-heading archive-year-number">{{ group.year }}</h2>
            <span class="ee-label">{{ group.articles.length }} 篇</span>
          </header>
          <ol class="archive-entries">
            <li v-for="article in group.articles" :key="article.id">
              <NuxtLink :to="article.public_path" data-focus-card class="archive-row">
                <span class="archive-row-connector" aria-hidden="true" />
                <span class="ee-heading archive-row-title">{{ article.title }}</span>
                <span class="archive-row-aux">
                  <span class="ee-label archive-row-meta">{{ archiveMeta(article) }}</span>
                  <time class="ee-label archive-row-date" :datetime="article.published_at">
                    {{ archiveDayStamp(article.published_at) }}
                  </time>
                </span>
              </NuxtLink>
            </li>
          </ol>
        </section>
      </div>
      <div v-else-if="!listBusy" data-focus-card class="empty-state mt-12">暂时还没有可归档的已发布文章。</div>
      <p v-if="listBusy" class="public-loading" role="status">正在读取内容…</p>
      <PaginationNav :page="page" :has-next="hasNext" path="/archive" />
    </div>
  </section>
</template>

<script setup lang="ts">
import SectionHeading from '~/components/SectionHeading.vue'
import PageHeroArtwork from '~/components/PageHeroArtwork.vue'
import type { PublicArticle } from '~/types/api'
import { groupArticlesByYear } from '~/utils/archive'
import { archiveDayStamp } from '~/utils/content'
import { paginatedApiPath, paginationWindow } from '~/utils/pagination'
import { readingMinutesFromContent } from '~/utils/readingTime'

const pageSize = 20
const page = useBoundedPage(pageSize)
const endpoint = computed(() => paginatedApiPath('/articles', page.value, pageSize))
const { data: articleRows, pending, error } = await useAsyncData(
  'archive-articles',
  (_nuxtApp, { signal }) => apiFetch<PublicArticle[]>(endpoint.value, { signal }),
  { watch: [endpoint] },
)
useApiFailure(error)
const window = computed(() => paginationWindow(articleRows.value, pageSize))
const groups = computed(() => groupArticlesByYear(window.value.items))
const hasNext = computed(() => window.value.hasNext)
const listBusy = computed(() => Boolean(pending.value))
const archiveMeta = (article: PublicArticle) => {
  const category = article.category?.name || '未分类'
  return `${category} · ${readingMinutesFromContent(article.content)} 分钟`
}

useSiteSeo(() => ({
  title: '归档',
  description: '按时间浏览 Gavin 已发布的技术文章。',
  jsonLd: {
    '@context': 'https://schema.org',
    '@type': 'CollectionPage',
    name: '文章归档',
    description: '按时间浏览 Gavin 已发布的技术文章。',
    inLanguage: 'zh-CN',
  },
}))
</script>

<style scoped>
.archive-page .archive-masthead {padding-bottom:0;}
.archive-masthead :deep(.site-section-heading) {margin-bottom:12px;}
.archive-hero-composition {display:grid;grid-template-columns:minmax(0,1fr) minmax(260px,32%);align-items:center;gap:32px;}
.archive-hero-composition :deep(.page-artwork) {max-width:340px;padding:14px 4px;margin-block:0;}
.archive-masthead-heading {font-size:clamp(28px,2.8vw,40px);line-height:1.4;}
.archive-masthead-note {max-width:38em;}
.archive-page .archive-spine {margin-top:36px;}
.archive-page .archive-year {display:block;padding:0 0 44px;}
.archive-page .archive-year-label {
  position:relative;display:flex;align-items:center;gap:20px;
  width:fit-content;max-width:100%;margin:0 0 0 2px;padding:14px 38px 14px 22px;
  color:var(--ee-surface);background:var(--ee-primary-strong);
  border-radius:4px 28px 4px 4px;
  box-shadow:6px 6px 0 color-mix(in srgb,var(--ee-primary-strong) 18%,transparent);
}
.archive-page .archive-year-label::before {display:none;}
.archive-page .archive-year-number {font-size:52px;font-weight:800;font-style:italic;line-height:1;letter-spacing:-.065em;color:inherit;}
.archive-page .archive-year-label .ee-label {margin:0;padding-left:18px;border-left:1px solid currentColor;color:inherit;font-size:13px;white-space:nowrap;}
.archive-page .archive-entries {
  position:relative;display:grid;gap:14px;margin:0 0 0 22px;padding:28px 0 8px 40px;
  border-left:0;
}
.archive-page .archive-entries::before {
  content:'';position:absolute;left:0;top:0;bottom:0;width:9px;
  border-inline:2px solid var(--ee-primary-strong);
  background:repeating-linear-gradient(to bottom,transparent 0 10px,color-mix(in srgb,var(--ee-primary-strong) 30%,transparent) 10px 12px);
}
.archive-page .archive-entries::after {
  content:'';position:absolute;left:-4px;bottom:-2px;width:17px;height:5px;
  border-radius:1px;background:var(--ee-primary-strong);
}
.archive-page .archive-entries > li {min-width:0;}
.archive-page .archive-row {
  position:relative;display:grid;grid-template-columns:64px minmax(0,1fr) auto;
  align-items:center;gap:18px;min-height:84px;padding:18px 22px;
  border:1px solid var(--ee-line);border-left:3px solid var(--ee-primary-strong);
  border-radius:3px 14px 14px 3px;background:var(--ee-surface);
}
.archive-page .archive-row::before {
  content:'';position:absolute;left:-44px;top:calc(50% - 8px);width:16px;height:16px;
  border:3px solid var(--ee-primary-strong);border-radius:3px;background:var(--ee-surface);
  transform:rotate(45deg);box-shadow:0 0 0 4px var(--ee-canvas);z-index:1;
}
.archive-page .archive-row-connector {
  content:'';position:absolute;left:-38px;top:calc(50% - 1px);width:36px;height:2px;
  background:var(--ee-primary-strong);
}
.archive-page .archive-row-title {font-size:18px;line-height:1.6;font-weight:600;overflow-wrap:anywhere;}
.archive-page .archive-row-date {font-size:16px;font-weight:600;color:var(--ee-primary-strong);white-space:nowrap;}
.archive-page .archive-row-date::after {content:none;}
.archive-page .archive-row-meta {font-size:13px;line-height:1.6;max-width:180px;}
.archive-page .archive-row:focus-visible {outline:3px solid var(--ee-primary-strong);outline-offset:4px;}
.archive-page .archive-row:focus-visible::before {background:var(--ee-primary-strong);}
@media(hover:hover) and (pointer:fine) {
  .archive-page .archive-row:hover {border-color:var(--ee-primary-strong);background:color-mix(in srgb,var(--ee-primary-strong) 5%,var(--ee-surface));}
  .archive-page .archive-row:hover::before {background:var(--ee-primary-strong);}
}
@media(max-width:767px) {
  .archive-page .archive-year {padding-bottom:32px;}
  .archive-page .archive-year-label {gap:16px;padding:12px 28px 12px 18px;}
  .archive-page .archive-year-number {font-size:42px;}
  .archive-page .archive-entries {margin-left:16px;padding:24px 0 8px 28px;gap:12px;}
  .archive-page .archive-row {grid-template-columns:48px minmax(0,1fr);gap:6px 12px;padding:16px 12px;}
  .archive-page .archive-row::before {left:-32px;width:16px;height:16px;}
  .archive-page .archive-row-connector {left:-26px;width:24px;}
  .archive-page .archive-row-title {font-size:16px;}
  .archive-page .archive-row-date {font-size:13px;}
  .archive-page .archive-row-meta {grid-column:2;grid-row:2;max-width:none;font-size:12px;}
}
@media(max-width:767px){.archive-hero-composition{grid-template-columns:minmax(0,1fr);gap:12px;}.archive-hero-composition :deep(.page-artwork){max-width:240px;padding:12px 6px;}.archive-masthead-heading{font-size:28px;}}
</style>
