<template>
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
    <template v-if="name === 'github'">
            <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3.3-.4 6.8-1.6 6.8-7A5.4 5.4 0 0 0 19.4 4 5 5 0 0 0 19.3.5S18.2.1 15 1.8a12.3 12.3 0 0 0-6 0C5.8.1 4.7.5 4.7.5A5 5 0 0 0 4.6 4a5.4 5.4 0 0 0-1.4 3.7c0 5.4 3.5 6.6 6.8 7A4.8 4.8 0 0 0 9 18v4" stroke-linecap="round" stroke-linejoin="round" />
            <path d="M9 19c-3 .9-3-1.5-4.2-2" stroke-linecap="round" stroke-linejoin="round" />
          </template>
    <template v-else-if="name === 'email'">
            <rect x="3" y="5" width="18" height="14" rx="2" />
            <path d="m3 7 9 6 9-6" stroke-linecap="round" stroke-linejoin="round" />
          </template>
    <template v-else-if="name === 'rss'"><circle cx="5" cy="19" r="1" /><path d="M4 11a9 9 0 0 1 9 9M4 4a16 16 0 0 1 16 16" /></template>
    <template v-else><rect x="3" y="4" width="18" height="16" rx="2" /><circle cx="8" cy="10" r="2" /><path d="M5 16c0-3 6-3 6 0m3-7h4m-4 4h4m-4 3h2" /></template>
  </svg>
</template>
<script setup lang="ts">
defineProps<{ name: 'github' | 'email' | 'rss' | 'profile' }>()
</script>
