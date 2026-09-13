<template>
  <nav
    v-if="page > 1 || hasNext"
    class="mt-10 flex items-center justify-center gap-4 border-t pt-7"
    style="border-color: var(--ee-line)"
    aria-label="分页"
  >
    <NuxtLink
      v-if="page > 1"
      :to="pageLink(path, page - 1, query)"
      class="button-secondary"
      rel="prev"
      data-testid="pagination-previous"
    >
      上一页
    </NuxtLink>
    <span class="ee-label tabular-nums" aria-current="page">第 {{ page }} 页</span>
    <NuxtLink
      v-if="hasNext"
      :to="pageLink(path, page + 1, query)"
      class="button-secondary"
      rel="next"
      data-testid="pagination-next"
    >
      下一页
    </NuxtLink>
  </nav>
</template>

<script setup lang="ts">
import { pageLink } from '~/utils/pagination'

defineProps<{
  page: number
  hasNext: boolean
  path: string
  query?: Record<string, string | number | null | undefined>
}>()
</script>
