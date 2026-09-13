<template>
  <div class="page-shell home-page">
    <section class="home-opening" data-testid="home-hero" aria-labelledby="home-heading">
      <SectionHeading label="技术与思考" />
      <HomeNotebookHero />
      <div class="home-hero-pair-grid">
        <div class="home-hero-column">
          <div class="home-panel-label">
            <h2>知识领域图谱</h2>
            <p>沿着知识路线，找到下一篇笔记。</p>
          </div>
          <HomeAtlas :content="content" :pending="pending" @retry="refresh()" />
        </div>
        <div v-if="profile" class="home-hero-column">
          <div class="home-panel-label">
            <h2>个人名片</h2>
            <p>了解我在做什么，以及如何联系我。</p>
          </div>
          <ProfileCard :profile="profile" variant="intro" />
        </div>
      </div>
    </section>
    <section class="home-notes" aria-labelledby="recent-heading" data-testid="home-latest" :aria-busy="pending">
      <SectionHeading label="最近更新" tag="h2" title-id="recent-heading" variant="section"><NuxtLink to="/archive" class="site-section-link">查看归档 <NavigationArrow /></NuxtLink></SectionHeading>
      <div v-if="pending && !content" data-focus-card class="home-empty" role="status">正在读取最近文章…</div>
      <div v-else-if="content?.articles.length" class="home-note-layout" :data-single="content.articles.length === 1">
        <article v-for="(article, index) in content.articles" :key="article.id" data-focus-card class="home-note blueprint-card" :class="index === 0 ? 'home-featured' : 'home-note-row'" :data-testid="index === 0 ? 'home-featured' : 'home-note-row'">
          <BlueprintWatermark :value="index + 1" />
          <div class="home-note-top">
            <time class="home-note-date" :datetime="article.published_at">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="5" width="16" height="16" rx="3" /><path d="M8 3v4m8-4v4M4 11h16m-12 4h3" /></svg>
              {{ homeDate(article.published_at) }}
            </time>
            <span v-if="article.category" class="status-chip" :class="['chip-blue', 'chip-emerald', 'chip-purple'][index % 3]">{{ article.category.name }}</span>
          </div>
          <h3><NuxtLink :to="article.public_path">{{ article.title }}</NuxtLink></h3>
          <p v-if="article.summary.trim()" class="home-note-summary">{{ article.summary }}</p>
          <div class="home-note-footer"><div class="home-note-specs"><span v-for="tag in article.tags?.slice(0, 1)" :key="tag.id" class="blueprint-spec">{{ tag.name }}</span><span v-if="article.readingMinutes" class="blueprint-spec">{{ article.readingMinutes }} min</span></div><NuxtLink :to="article.public_path" :aria-label="`阅读全文：${article.title}`" class="blueprint-arrow"><NavigationArrow /></NuxtLink></div>
        </article>
      </div>
      <div v-else data-focus-card class="home-empty" data-testid="home-empty"><p>第一篇文章正在路上。</p><p>新的工程笔记发布后，会出现在这里。</p></div>
    </section>
  </div>
</template>

<script setup lang="ts">
import SectionHeading from '~/components/SectionHeading.vue'
import HomeNotebookHero from '~/components/HomeNotebookHero.vue'
import { absoluteSiteUrl } from '~/utils/site'
import { homeDate, loadHomeContent } from '~/utils/home'

const { data: content, pending, error: articlesError, refresh } = await useAsyncData(
  'home-content',
  (nuxtApp, { signal }) => {
    function fetchHome<T>(path: string) {
      return nuxtApp.runWithContext(() => apiFetch<T>(path, { signal, retry: 0 }))
    }
    return loadHomeContent(fetchHome, signal)
  },
  { lazy: true },
)
const { data: profile, error: profileError } = await usePublicProfile()
useApiFailure(articlesError)
useApiFailure(profileError)
const config = useRuntimeConfig()
useSiteSeo(() => ({
  title: '技术与思考', description: 'Gavin 的开发笔记、项目记录与读书心得。',
  jsonLd: {
    '@context': 'https://schema.org', '@type': 'WebSite', name: 'Gavin',
    description: 'Gavin 的开发笔记、项目记录与读书心得。',
    url: absoluteSiteUrl(config.public.siteUrl, '/'), inLanguage: 'zh-CN',
    potentialAction: websiteSearchAction(config.public.siteUrl),
  },
}))
</script>

<style scoped>
/* Keep the style module available for existing development sessions after reverting the preview. */
</style>
