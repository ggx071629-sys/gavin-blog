<template>
  <button
    v-if="entry.visible.value" type="button" class="assistant-launcher" aria-haspopup="dialog"
    :aria-expanded="entry.open.value" aria-controls="ask-gavin-panel" aria-label="问 Gavin"
    data-testid="assistant-launcher" data-assistant-entry="header" @click="entry.activate('header')">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M5 4h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-6 3V6a2 2 0 0 1 2-2Z" stroke-linejoin="round"/><path d="M8 9h8M8 13h5" stroke-linecap="round"/></svg>
    <span>问 Gavin</span>
  </button>
</template>
<script setup lang="ts">
const entry = useAssistantEntry()
</script>
<style scoped>
.assistant-launcher {position:static;display:inline-flex;flex-shrink:0;align-items:center;justify-content:center;gap:8px;min-height:44px;padding:0 14px;border:1px solid color-mix(in srgb,var(--ee-primary) 45%,var(--ee-line));border-radius:10px;background:color-mix(in srgb,var(--ee-primary) 7%,var(--ee-surface));color:var(--ee-accent-text);font:600 14px/1.5 var(--ee-heading);white-space:nowrap;box-shadow:none;}
.assistant-launcher:hover {border-color:var(--ee-primary);background:color-mix(in srgb,var(--ee-primary) 12%,var(--ee-surface));}
.assistant-launcher:focus-visible {outline:2px solid var(--ee-focus);outline-offset:3px;}
</style>
