<template>
  <svg
    class="navigation-arrow"
    :data-direction="direction"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.6"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    focusable="false"
  >
    <path v-if="direction === 'up-right'" d="M5 19 19 5M7 5h12v12" />
    <path v-else-if="direction === 'left'" d="M21 12H3m8-8-8 8 8 8" />
    <path v-else d="M3 12h18m-8-8 8 8-8 8" />
  </svg>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ direction?: 'right' | 'up-right' | 'left' }>(), { direction: 'right' })
</script>

<style scoped>
.navigation-arrow {
  display: inline-block;
  width: var(--navigation-arrow-size, 16px);
  height: var(--navigation-arrow-size, 16px);
  flex: 0 0 auto;
  vertical-align: middle;
}
@media (hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference) {
  .navigation-arrow { transition: transform var(--ee-motion-fast) cubic-bezier(0.23, 1, 0.32, 1); }
  :global(a:hover .navigation-arrow) { transform: translateX(3px); }
  :global(a:hover .navigation-arrow[data-direction='up-right']) { transform: translate(2px, -2px); }
  :global(a:hover .navigation-arrow[data-direction='left']) { transform: translateX(-3px); }
  :global(a:focus-visible .navigation-arrow) { transition: none; transform: none; }
}
</style>
