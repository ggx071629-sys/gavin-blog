<template>
  <svg class="site-nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path :d="paths[name]" />
  </svg>
</template>

<script setup lang="ts">
defineProps<{ name: 'articles' | 'projects' | 'books' | 'archive' | 'about' | 'search' }>()
const paths = {
  articles: 'M5 3h10l4 4v14H5Z M14 3v5h5 M8 12h8 M8 16h5',
  projects: 'm8 7-5 5 5 5 M16 7l5 5-5 5 M14 4l-4 16',
  books: 'M12 5C9 3 6 3 3 4v15c3-1 6-1 9 1 3-2 6-2 9-1V4c-3-1-6-1-9 1Z M12 5v15',
  archive: 'M3 4h18v5H3Z M5 9v12h14V9 M9 13h6',
  about: 'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0 M4 21v-2a8 8 0 0 1 16 0v2',
  search: 'M18 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0 M16 16l5 5',
}
</script>
