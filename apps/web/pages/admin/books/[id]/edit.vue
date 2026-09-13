<template><BookNoteEditor v-if="note" :note="note" @saved="note = $event" /></template>
<script setup lang="ts">
import type { BookNote } from '~/types/api'
definePageMeta({ layout: 'admin-core', middleware: 'admin' })
const route = useRoute()
const { data: note, error } = await useAsyncData(`admin-book-${route.params.id}`, () => apiFetch<BookNote>(`/admin/books/${route.params.id}`))
useApiFailure(error, '读书笔记不存在')
useSeoMeta({ title: () => note.value?.book_title || '编辑读书笔记' })
</script>
