<template>
  <button
    class="theme-switch"
    :class="{ 'theme-switch--admin': admin }"
    type="button"
    aria-label="切换颜色主题"
    :aria-pressed="isDark"
    title="切换颜色主题"
    :data-testid="admin ? 'admin-theme-toggle' : 'theme-toggle'"
    @click="toggleTheme"
  >
    <span class="theme-switch-track" aria-hidden="true">
      <span class="theme-switch-thumb" />
      <svg class="theme-switch-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round">
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.66 6.34l1.41-1.41" />
      </svg>
      <svg class="theme-switch-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round">
        <path d="M20.2 15.1A8.5 8.5 0 0 1 8.9 3.8 8.5 8.5 0 1 0 20.2 15.1Z" />
      </svg>
    </span>
    <span class="sr-only">{{ isDark ? '当前为深色模式' : '当前为浅色模式' }}</span>
  </button>
</template>

<script setup lang="ts">
defineProps<{ admin?: boolean }>()
const colorMode = useColorMode()
const hydrated = ref(false)
onMounted(() => { hydrated.value = true })
const isDark = computed(() => hydrated.value && colorMode.value === 'dark')
const toggleTheme = () => {
  colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'
}
</script>

<style scoped>
.theme-switch {display:inline-flex;align-items:center;justify-content:center;flex:0 0 64px;width:64px;min-height:44px;padding:0;border:0;border-radius:24px;background:transparent;cursor:pointer;}
.theme-switch-track {position:relative;display:block;width:60px;height:32px;border:1px solid var(--ee-line);border-radius:20px;background:var(--ee-surface-low);}
.theme-switch-thumb {position:absolute;top:2px;left:2px;width:26px;height:26px;border-radius:50%;background:var(--ee-surface);box-shadow:0 1px 4px #0002;}
.theme-switch svg {position:absolute;top:7px;width:16px;height:16px;}
.theme-switch-sun {left:7px;color:var(--ee-ink);}
.theme-switch-moon {right:7px;color:var(--ee-ink-muted);}
:global(.dark .theme-switch-thumb) {transform:translateX(28px);background:var(--ee-ink);}
:global(.dark .theme-switch-moon) {color:var(--ee-canvas);}
:global(.dark .theme-switch-sun) {color:var(--ee-ink-muted);}
.theme-switch:focus-visible {outline:2px solid var(--ee-primary);outline-offset:3px;}
@media(hover:hover) and (pointer:fine) {.theme-switch:hover .theme-switch-track {border-color:var(--ee-primary);}}
@media(prefers-reduced-motion:no-preference) {.theme-switch-thumb {transition:transform var(--ee-motion-fast) cubic-bezier(0.23,1,0.32,1);}}
</style>
