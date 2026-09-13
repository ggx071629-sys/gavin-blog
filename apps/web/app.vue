<template>
  <div class="contents" data-testid="app-root" :data-hydrated="hydrated">
    <NuxtLoadingIndicator color="var(--ee-primary)" />
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </div>
</template>

<script setup lang="ts">
usePublicCardFocus()

const hydrated = ref(false)
onMounted(() => { hydrated.value = true })
</script>
