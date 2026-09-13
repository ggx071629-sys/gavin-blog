<template>
  <article data-focus-card class="book-ledger-row blueprint-card group" data-testid="book-card">
    <NuxtLink :to="note.public_path" class="book-ledger-link">
      <span class="book-ledger-top"><span v-if="note.rating != null" class="book-ledger-rating" :aria-label="`评分 ${note.rating} / 5`"><span aria-hidden="true">{{ '★ '.repeat(note.rating) }}<span class="book-rating-empty">{{ '☆ '.repeat(5 - note.rating) }}</span></span></span><span v-else class="status-chip" :class="note.reading_status === 'reading' ? 'chip-emerald' : 'chip-blue'">{{ readingStatusLabel(note.reading_status) }}</span><time class="book-ledger-date" :datetime="note.reading_date || note.published_at">{{ ledgerMonth }}</time></span>
      <span class="book-ledger-book"><span class="book-ledger-title">{{ note.book_title }}</span><span class="book-ledger-author">{{ note.author }}</span><span v-if="note.summary" class="book-ledger-summary">{{ note.summary }}</span></span>
      <span class="book-ledger-footer"><span class="book-ledger-status">{{ readingStatusLabel(note.reading_status) }} · 书摘笔记</span><NavigationArrow /></span>
    </NuxtLink>
  </article>
</template>

<script setup lang="ts">
import type { PublicBookNote } from '~/types/api'
import { bookLedgerMonth, readingStatusLabel } from '~/utils/content'

const props = defineProps<{
  note: PublicBookNote
}>()

const ledgerMonth = computed(() => bookLedgerMonth(props.note.reading_date, props.note.published_at))
</script>
