<template>
  <svg class="geometric-mark" :data-active="active" :data-variant="variant" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
    <path v-for="(part, partIndex) in marks[variant]" :key="partIndex" :d="part" />
  </svg>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{ index?: number; active?: boolean }>(), { index: 0, active: false })
const variant = computed(() => ((Math.trunc(props.index) % marks.length) + marks.length) % marks.length)
// Abstract geometry stays independent of editable card content.
const marks = [
  ['m12 3 9 5-9 5-9-5 9-5Z', 'M3 12l9 5 9-5', 'M3 16l9 5 9-5'],
  ['M4 4h6v6H4z', 'M14 4h6v6h-6z', 'M14 14h6v6h-6z', 'M4 14h6v6H4z'],
  ['M15 9a6 6 0 1 1-12 0 6 6 0 0 1 12 0Z', 'M21 15a6 6 0 1 1-12 0 6 6 0 0 1 12 0Z'],
  ['m12 2 4 5-4 5-4-5 4-5Z', 'm12 12 4 5-4 5-4-5 4-5Z', 'm2 12 5-4 5 4-5 4-5-4Z', 'm12 12 5-4 5 4-5 4-5-4Z'],
  ['M4 4h12v12H4z', 'M8 8h12v12H8z'],
  ['M12 3a9 9 0 1 1-9 9', 'M12 7a5 5 0 1 1-5 5', 'M3 3l9 9'],
  // Prism, constellation, waveform, and compass complete the ten-card set.
  ['m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z', 'm4 7.5 8 4.5 8-4.5', 'M12 12v9'],
  ['m7 7 10 10M7 17 17 7', 'M9 5a2 2 0 1 1-4 0 2 2 0 0 1 4 0ZM19 19a2 2 0 1 1-4 0 2 2 0 0 1 4 0Z', 'M19 5a2 2 0 1 1-4 0 2 2 0 0 1 4 0ZM9 19a2 2 0 1 1-4 0 2 2 0 0 1 4 0Z'],
  ['M4 9v6', 'M9 5v14', 'M15 3v18', 'M20 8v8'],
  ['M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z', 'm16 8-2 6-6 2 2-6 6-2Z'],
]
</script>

<style scoped>
.geometric-mark {overflow:visible;}
path {transform-box:fill-box;transform-origin:center;}
[data-variant="5"] path:last-child {transform-box:view-box;}
@media(hover:hover) and (pointer:fine) and (prefers-reduced-motion:no-preference) {
  path {transition:transform var(--ee-motion-fast, 180ms) cubic-bezier(.23,1,.32,1);}
  [data-active="true"][data-variant="0"] path:first-child {transform:translateY(-2px);}
  [data-active="true"][data-variant="0"] path:last-child {transform:translateY(2px);}
  [data-active="true"][data-variant="1"] path {transform:scale(.85) rotate(12deg);}
  [data-active="true"][data-variant="2"] path:first-child {transform:translate(-1px,-1px);}
  [data-active="true"][data-variant="2"] path:last-child {transform:translate(1px,1px);}
  [data-active="true"][data-variant="3"] path {transform:scale(.85) rotate(15deg);}
  [data-active="true"][data-variant="4"] path:first-child {transform:translateX(-1px) rotate(-5deg);}
  [data-active="true"][data-variant="4"] path:last-child {transform:translateX(1px) rotate(5deg);}
  [data-active="true"][data-variant="5"] path:last-child {transform:rotate(20deg);}
  [data-active="true"][data-variant="6"] path {transform:translateY(-1px);}
  [data-active="true"][data-variant="6"] path:first-child {transform:translateY(-1px) scale(1.06);}
  [data-active="true"][data-variant="7"] path:not(:first-child) {transform:scale(1.1);}
  [data-active="true"][data-variant="8"] path:nth-child(odd) {transform:scaleY(.75);}
  [data-active="true"][data-variant="8"] path:nth-child(even) {transform:scaleY(1.15);}
  [data-active="true"][data-variant="9"] path:last-child {transform:rotate(30deg);}
}
</style>
