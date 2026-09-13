<template>
  <section class="resource-ops studio-taxonomy">
    <div class="max-w-2xl">
      <h1 class="mt-3 text-3xl font-semibold tracking-tight">栏目与标签</h1>
      <p class="mt-3 text-sm leading-7 text-ee-ink-faint">
        栏目表达文章的主归属，标签用于跨栏目连接主题。已被文章使用的项目需先解除关联才能删除。
      </p>
    </div>
    <nav aria-label="分类分区" class="taxonomy-sections"><a href="#taxonomy-categories">栏目</a><a href="#taxonomy-tags">标签</a></nav>
    <div class="mt-6 grid gap-6">
      <TaxonomyManager title="栏目" kind="categories" :items="categories || []" />
      <TaxonomyManager title="标签" kind="tags" :items="tags || []" />
    </div>
  </section>
</template>

<script setup lang="ts">
import '~/assets/css/resource-operations.css'
import type { TaxonomyItem } from '~/types/api'

definePageMeta({ layout: 'admin-core', middleware: 'admin' })
const { data: categories, error: categoriesError } = await useAsyncData('admin-categories', () =>
  apiFetch<TaxonomyItem[]>('/admin/categories'),
)
const { data: tags, error: tagsError } = await useAsyncData('admin-tags', () =>
  apiFetch<TaxonomyItem[]>('/admin/tags'),
)
useApiFailure(categoriesError)
useApiFailure(tagsError)
useSeoMeta({ title: '栏目与标签' })
</script>

<style scoped>
.studio-taxonomy { max-width: none; margin: 0; --ee-ink-faint: var(--studio-muted); }
.studio-taxonomy h1 { font-size: 36px; margin: 0; }
.taxonomy-sections { display: flex; gap: 20px; margin-top: 24px; border-bottom: 1px solid var(--studio-divider); }
.taxonomy-sections a { min-height: 54px; display: inline-flex; align-items: center; padding-inline: 16px; color: var(--studio-muted); }
.taxonomy-sections a:hover { color: var(--studio-primary); background: var(--studio-low); }
@media (max-width: 760px) { .studio-taxonomy h1 { font-size: 28px; } }
</style>
