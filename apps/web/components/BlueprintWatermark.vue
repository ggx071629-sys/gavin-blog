<template>
  <svg class="blueprint-watermark" viewBox="0 0 190 110" aria-hidden="true" focusable="false">
    <text x="190" y="96" text-anchor="end">{{ String(value).padStart(2, '0') }}</text>
  </svg>
</template>
<script setup lang="ts">
defineProps<{ value: string | number }>()
</script>
<style scoped>
.blueprint-watermark { position: absolute; right: -8px; bottom: -20px; width: 190px; height: 110px; pointer-events: none; user-select: none; opacity: .045; transition: opacity 200ms; overflow: visible; }
text { font-family: var(--ee-heading); font-size: 108px; font-weight: 700; letter-spacing: -5px; fill: currentColor; }
:global(.dark .blueprint-watermark) { opacity: .055; }
:global(.blueprint-card:hover .blueprint-watermark) { opacity: .1; }
@media (prefers-reduced-motion: reduce) { .blueprint-watermark { transition: none; } }
</style>
