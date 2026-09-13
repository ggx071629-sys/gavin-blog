<template>
  <div class="reading-layout" :class="{ 'reading-layout--plain': !headings.length }">
    <aside v-if="headings.length" class="reading-toc">
      <ContentToc :headings="headings" :reading-minutes="readingMinutes" />
    </aside>
    <div class="reading-body article-reading-main" data-article-body>
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { MarkdownHeading } from '~/utils/markdown'

withDefaults(defineProps<{ headings: MarkdownHeading[], readingMinutes?: number }>(), { readingMinutes: 1 })
</script>
