<template>
  <section v-if="page" class="admin-draft-preview about-preview studio-about-preview">
    <NuxtLink to="/admin/about" class="admin-back-link"><NavigationArrow direction="left" /> 返回编辑</NuxtLink>
    <header class="admin-page-header"><div><p class="admin-page-title">关于页预览</p><p class="admin-page-description">核对已保存的工作副本与共用身份资料。</p></div><NuxtLink to="/admin/about/revisions" class="button-secondary">版本历史</NuxtLink></header>
    <div class="admin-draft-banner" role="status" data-testid="about-preview-banner">
      <span v-if="page.status === 'published'">
        <strong>已发布</strong><span aria-hidden="true"> · </span><span>工作副本预览，公开站点仍显示当前发布修订。</span>
      </span>
      <span v-else>
        <strong>未公开</strong><span aria-hidden="true"> · </span><span>草稿预览，不会出现在公开站点。</span>
      </span>

    </div>
    <div class="blueprint-wrapper">
      <AboutPublicBody :content="page.content" :profile="profile ?? null" />
    </div>
    <section class="about-preview-fields" aria-labelledby="about-fields-title">
      <h2 id="about-fields-title">编辑字段核对</h2>
      <p class="about-fields-note">以下字段已保存在工作副本中，当前公开模板尚未展示。</p>
      <h3>引言</h3><p data-testid="about-preview-statement">{{ page.content.statement || '尚未填写引言。' }}</p>
      <h3>写作范围</h3><ul><li v-for="topic in page.content.editorial_topics" :key="topic">{{ topic }}</li></ul>
    </section>
  </section>
</template>

<script setup lang="ts">
import type { AboutPageAdmin, ProfilePublic } from '~/types/api'

definePageMeta({ layout: 'admin-core', middleware: 'admin' })

const { data: page, error } = await useAsyncData<AboutPageAdmin>(
  'about-page-preview',
  () => apiFetch<AboutPageAdmin>('/admin/about-page'),
)
useApiFailure(error, '关于页不存在')

const { data: profile, error: profileError } = await useAsyncData<ProfilePublic>(
  'about-preview-profile',
  () => apiFetch<ProfilePublic>('/profile'),
)
useApiFailure(profileError)

useSeoMeta({ title: () => `预览：关于页 #${page.value?.version || ''}` })
</script>

<style scoped>
.studio-about-preview { max-width: none; min-width: 0; --ee-ink-faint: var(--studio-muted); }
.studio-about-preview .blueprint-wrapper { margin-top: 32px; border-top: 1px solid var(--studio-divider); }
.studio-about-preview :deep(.about-editorial) { padding-inline: 0; min-width: 0; }
.studio-about-preview :deep(.ae-introduction) { grid-template-columns: minmax(0, 1fr); }
.studio-about-preview :deep(.ae-profile-card) { max-width: 660px; }
.studio-about-preview :deep(.ae-domains) { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.about-preview-fields { margin-top: 40px; padding-top: 28px; border-top: 1px solid var(--studio-divider); overflow-wrap: anywhere; }
.about-preview-fields h2 { font-size: 22px; font-weight: 600; }
.about-preview-fields h3 { margin-top: 24px; font-weight: 600; }
.about-preview-fields p, .about-preview-fields ul { margin-top: 12px; line-height: 1.8; }
.about-fields-note { color: var(--studio-muted); }
@media (max-width: 760px) { .studio-about-preview :deep(.ae-domains) { grid-template-columns: minmax(0, 1fr); } }
</style>
