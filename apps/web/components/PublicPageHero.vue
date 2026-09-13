<template>
  <header class="public-page-hero space-y-4">
    <SectionHeading :label="label" />
    <div class="page-hero-composition" :class="{ 'page-hero-with-art': artwork }">
    <div class="space-y-3 page-hero-copy">
      <h1 class="ee-heading public-page-title font-black tracking-tight text-[var(--ee-ink)]">{{ title }}</h1>
      <p v-if="description" class="public-page-description text-[var(--ee-ink-muted)] font-medium leading-relaxed">{{ description }}</p>
    </div>
    <PageHeroArtwork v-if="artwork" :kind="artwork" />
    </div>
  </header>
</template>

<script setup lang="ts">
import SectionHeading from '~/components/SectionHeading.vue'
import PageHeroArtwork from '~/components/PageHeroArtwork.vue'
defineProps<{
  label: string
  title: string
  description?: string
  artwork?: 'articles' | 'projects' | 'books'
}>()
</script>

<style scoped>
.page-hero-with-art {display:grid;grid-template-columns:minmax(0,1fr) minmax(260px,32%);align-items:center;gap:32px;padding:0;}
.public-page-hero :deep(.site-section-heading) {margin-bottom:12px;}
.page-hero-with-art :deep(.page-artwork) {max-width:340px;padding:14px 4px;margin-block:0;}
.page-hero-with-art .public-page-title {font-size:clamp(28px,2.8vw,40px);line-height:1.35;}
.page-hero-copy {min-width:0;}
.page-hero-with-art .public-page-description {font-size:17px;line-height:1.85;max-width:38em;}
@media(max-width:767px) {.page-hero-with-art{grid-template-columns:minmax(0,1fr);gap:12px;padding:0;}.page-hero-with-art :deep(.page-artwork){max-width:240px;padding:12px 6px;}.page-hero-with-art .public-page-title{font-size:28px;}.page-hero-with-art .public-page-description{font-size:16px;}}
</style>
