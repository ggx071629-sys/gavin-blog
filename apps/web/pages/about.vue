<template>
  <AboutPublicBody :content="content ?? null" :profile="profile ?? null" />
</template>

<script setup lang="ts">
import type { AboutPageContent, ProfilePublic } from '~/types/api'

const { data: profile, error: profileError } = await useAsyncData(
  'public-profile-about',
  () => apiFetch<ProfilePublic>('/profile'),
)
const { data: content, error: contentError } = await useAsyncData(
  'public-about-content',
  () => apiFetch<AboutPageContent>('/about-page'),
)
useApiFailure(profileError)
useApiFailure(contentError)

useSiteSeo(() => ({
  title: '关于',
  description: '了解 Gavin 的技术方向、近期动态与联系方式。',
  jsonLd: {
    '@context': 'https://schema.org',
    '@type': 'AboutPage',
    name: '关于 Gavin',
    description: '了解 Gavin 的技术方向、近期动态与联系方式。',
    inLanguage: 'zh-CN',
  },
}))
</script>
