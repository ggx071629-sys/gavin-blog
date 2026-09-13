<template>
  <div class="flex min-h-screen flex-col blueprint-wrapper">
    <a href="#main-content" class="skip-link">跳到正文</a>
    <SiteHeader />
    <main id="main-content" class="flex-1" tabindex="-1">
      <slot />
    </main>
    <AssistantHost v-if="assistantUiEnabled" />
    <SiteFooter :github-url="footerProfile?.github_url" />
  </div>
</template>

<script setup lang="ts">
import { isAssistantUiEnabled } from '~/utils/assistant/flag'

const { data: footerProfile } = await usePublicProfile()
const config = useRuntimeConfig()
useAssistantAvailability()
const assistantUiEnabled = isAssistantUiEnabled(config.public.assistantUiEnabled)
</script>
