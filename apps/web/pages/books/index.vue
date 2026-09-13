<template>
  <section class="page-shell public-page books-index max-w-4xl mx-auto space-y-6">
    <PublicPageHero
      class="books-intro"
      label="阅读书架"
      artwork="books"
      title="读过的书与读书笔记"
      description="记录正在读和读过的书，整理书中摘录、个人理解，以及值得继续思考的问题。"
    />

    <section v-if="currentReading" class="books-reading-section">
      <p class="blueprint-section-caption">正在阅读</p>
      <div data-focus-card class="books-current blueprint-card" data-testid="books-current">
        <div class="books-current-main">
          <img v-if="currentReading.cover_url && !coverFailed" :src="currentReading.cover_url" :alt="`${currentReading.book_title} 封面`" class="books-current-cover" @error="coverFailed = true">
          <div v-else class="book-spine" aria-hidden="true"><span>READING</span><strong>{{ currentReading.book_title }}</strong><span>{{ currentReading.author }}</span></div>
          <div class="books-current-identity"><span class="status-chip chip-emerald">在读</span><h2 class="books-current-title">{{ currentReading.book_title }}</h2><p class="books-current-author">{{ currentReading.author }}</p><p v-if="currentReading.summary" class="books-current-note">“{{ currentReading.summary }}”</p></div>
        </div>
        <NuxtLink :to="currentReading.public_path" class="blueprint-button blueprint-button-primary books-current-cta">阅读书摘笔记 <NavigationArrow /></NuxtLink>
      </div>
    </section>

    <div class="books-results space-y-10" data-testid="books-results" :aria-busy="listBusy ? 'true' : 'false'">
      <div v-if="notes.length" class="space-y-6">
        <header class="books-ledger-header"><h2 class="books-ledger-heading">书目与笔记归档</h2></header>
        <div class="books-ledger">
          <BookCard v-for="note in notes" :key="note.id" :note="note" />
        </div>
      </div>
      <div v-else-if="!listBusy" data-focus-card class="empty-state mt-12">暂时还没有已发布读书笔记。</div>
      <p v-if="listBusy" class="public-loading" role="status">正在读取内容…</p>
      <PaginationNav :page="page" :has-next="hasNext" path="/books" />
    </div>
  </section>
</template>

<script setup lang="ts">
import type { PublicBookNote } from '~/types/api'
import { paginatedApiPath, paginationWindow } from '~/utils/pagination'

const pageSize = 12
const page = useBoundedPage(pageSize)
const endpoint = computed(() => paginatedApiPath('/books', page.value, pageSize))
const { data: noteRows, pending, error } = await useAsyncData(
  'books',
  (_nuxtApp, { signal }) => apiFetch<PublicBookNote[]>(endpoint.value, { signal }),
  { watch: [endpoint] },
)
useApiFailure(error)
const window = computed(() => paginationWindow(noteRows.value, pageSize))
const notes = computed(() => window.value.items)
const hasNext = computed(() => window.value.hasNext)
const listBusy = computed(() => Boolean(pending.value))
const currentReading = computed(() => notes.value.find(note => note.reading_status === 'reading') || null)
const coverFailed = ref(false)
watch(() => currentReading.value?.cover_url, () => { coverFailed.value = false })

useSiteSeo(() => ({
  title: '读书笔记',
  description: 'Gavin 的阅读书单、书中摘录与个人读书心得。',
  jsonLd: {
    '@context': 'https://schema.org',
    '@type': 'CollectionPage',
    name: '读书笔记',
    description: 'Gavin 的阅读书单、书中摘录与个人读书心得。',
    inLanguage: 'zh-CN',
  },
}))
</script>
