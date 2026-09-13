<template>
  <footer class="site-footer">
    <div class="page-shell site-footer-inner">
      <strong class="site-footer-brand">GAVIN</strong>
      <p class="site-footer-credit">© {{ new Date().getFullYear() }} Gavin</p>
      <nav aria-label="页脚导航" class="site-footer-links">
        <a v-if="githubUrl" :href="githubUrl" rel="noreferrer" target="_blank">
          <svg class="site-footer-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3.3-.4 6.8-1.6 6.8-7A5.4 5.4 0 0 0 19.4 4 5 5 0 0 0 19.3.5S18.2.1 15 1.8a12.3 12.3 0 0 0-6 0C5.8.1 4.7.5 4.7.5A5 5 0 0 0 4.6 4a5.4 5.4 0 0 0-1.4 3.7c0 5.4 3.5 6.6 6.8 7A4.8 4.8 0 0 0 9 18v4" />
            <path d="M9 19c-3 .9-3-1.5-4.2-2" />
          </svg>
          <span>GitHub</span>
        </a>
        <a href="/rss.xml">
          <svg class="site-footer-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M4 4a16 16 0 0 1 16 16M4 11a9 9 0 0 1 9 9" />
            <circle cx="5" cy="19" r="1" fill="currentColor" />
          </svg>
          <span>RSS</span>
        </a>
        <NuxtLink to="/about">
          <svg class="site-footer-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <circle cx="12" cy="8" r="4" />
            <path d="M5 21v-2a7 7 0 0 1 14 0v2" />
          </svg>
          <span>About</span>
        </NuxtLink>
      </nav>
    </div>
  </footer>
</template>

<script setup lang="ts">
defineProps<{ githubUrl?: string | null }>()
</script>
