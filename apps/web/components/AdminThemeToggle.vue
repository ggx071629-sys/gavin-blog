<template>
  <button
    class="studio-theme-toggle"
    :class="{ 'studio-theme-toggle-compact': compact }"
    type="button"
    aria-label="切换颜色主题"
    :aria-pressed="isDark"
    data-testid="admin-theme-toggle"
    @click="colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'"
  >
    <StudioIcon class="studio-theme-sun" name="sun" />
    <StudioIcon class="studio-theme-moon" name="moon" />
    <span v-if="!compact">切换主题</span>
    <span class="sr-only">{{ isDark ? '当前为深色模式' : '当前为浅色模式' }}</span>
  </button>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ compact?: boolean }>(), { compact: true })
const colorMode = useColorMode()
const hydrated = ref(false)
onMounted(() => { hydrated.value = true })
const isDark = computed(() => hydrated.value && colorMode.value === 'dark')
</script>
