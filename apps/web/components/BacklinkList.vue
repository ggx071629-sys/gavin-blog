<template>
  <section v-if="items.length" class="references-panel" aria-labelledby="backlinks-title" data-testid="content-backlinks">
    <p class="eyebrow">Linked from / 链入</p>
    <h2 id="backlinks-title" class="ee-heading mt-3 text-2xl font-bold">被以下内容引用</h2>
    <div class="mt-5 grid gap-3 sm:grid-cols-2">
      <NuxtLink
        v-for="item in items"
        :key="`${item.content_type}-${item.id}`"
        :to="item.public_path"
        data-focus-card class="article-related-link"
      >
        <span class="eyebrow">{{ typeLabel[item.content_type] }}</span>
        <strong>{{ item.title }}</strong>
        <span v-if="item.summary">{{ item.summary }}</span>
      </NuxtLink>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { ContentType, PublicBacklink } from '~/types/api'

defineProps<{ items: PublicBacklink[] }>()

const typeLabel: Record<ContentType, string> = {
  article: '文章',
  project: '项目',
  book: '读书',
}
</script>
