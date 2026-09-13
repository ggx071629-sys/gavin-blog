<template>
  <span class="studio-icon" aria-hidden="true" :style="{ '--studio-icon': `url(/studio/icons/${name}.svg)` }" />
</template>

<script setup lang="ts">
defineProps<{
  name: 'file-description' | 'book' | 'folder' | 'user-square' | 'info-circle'
    | 'tag' | 'photo' | 'trash' | 'message-circle' | 'sun' | 'moon'
    | 'external-link' | 'arrow-left' | 'x' | 'plus' | 'search'
    | 'check' | 'alert-circle' | 'alert-circle-filled' | 'dots' | 'refresh'
    | 'settings' | 'send' | 'chevron-right' | 'message-dots' | 'message-circle-filled'
}>()
</script>
