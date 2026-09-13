<template>
  <div class="page-shell public-page about-editorial">
    <section class="ae-section">
      <SectionHeading label="关于我" />
      <div class="ae-introduction">
        <div class="about-signature-intro"><h1>你好，我是 <span>{{ profile?.name || 'Gavin' }}</span>。</h1><p class="about-page-intro">这里介绍我的技术方向、最近在做的事，以及联系方式。</p><PageHeroArtwork kind="about" :name="profile?.name" /></div>
        <div v-if="profile" class="ae-profile-card" data-testid="about-coordinates">
          <ProfileCard :profile="profile" variant="intro" aria-label="公开个人资料" />
        </div>
      </div>
    </section>

    <section v-if="content?.statement || content?.editorial_topics.length" class="ae-section" aria-label="自述与写作主题">
      <SectionHeading label="自述与写作" />
      <div class="ae-panel">
        <p v-if="content.statement" style="white-space: pre-wrap">{{ content.statement }}</p>
        <template v-if="content.editorial_topics.length">
          <h2>写作主题</h2>
          <ul class="ae-tags"><li v-for="topic in content.editorial_topics" :key="topic">{{ topic }}</li></ul>
        </template>
      </div>
    </section>

    <section v-if="content" class="ae-section">
      <SectionHeading label="能力与实践" />
      <div class="ae-section-title"><h2>我能做什么</h2><span>[ {{ content.capabilities.length }} DOMAINS ]</span></div>
      <div class="ae-domains">
        <article
          v-for="(domain, index) in content.capabilities"
          :key="domain.title"
          data-focus-card class="ae-domain about-capability blueprint-card"
          @pointerenter="activeCapability = $event.pointerType === 'mouse' ? index : null"
          @pointerleave="activeCapability = null"
        >
          <div class="capability-icon" aria-hidden="true">
            <GeometricMark :index="index" :active="activeCapability === index" />
          </div>
          <h3>{{ domain.title }}</h3><p>{{ domain.description }}</p>
          <ul v-if="domain.tags.length" class="ae-tags"><li v-for="tag in domain.tags" :key="tag">{{ tag }}</li></ul>
        </article>
      </div>
    </section>

    <section v-if="content?.now.length" class="ae-section">
      <SectionHeading label="近期动态" />
      <div class="ae-section-title"><h2>最近在做</h2></div>
      <div class="ae-now">
        <NuxtLink
          v-for="item in content.now"
          :key="item.label"
          data-focus-card
          :to="'/' + item.target"
        >
          <span><b aria-hidden="true"><NavigationArrow /></b>{{ item.label }}</span>
          <small :class="[NOW_STATUS[item.status].chip, 'status-chip']">{{ NOW_STATUS[item.status].label }}</small>
        </NuxtLink>
      </div>
    </section>

    <section v-if="content" class="ae-section">
      <SectionHeading label="关于本站" />
      <div data-focus-card class="ae-panel ae-site">
        <h2>关于这个网站</h2><p>{{ content.site.description }}</p>
        <dl v-if="content.site.stack.length">
          <div v-for="item in content.site.stack" :key="item.label" data-focus-card><dt>{{ item.label }}</dt><dd>{{ item.value }}</dd></div>
        </dl>
      </div>
    </section>

    <section class="ae-section">
      <SectionHeading label="保持联系" />
      <div class="ae-section-title"><h2>找到我</h2></div>
      <nav class="ae-channels" aria-label="联系方式">
        <a
          v-for="channel in channels"
          :key="channel.icon"
          data-focus-card
          :href="channel.href"
          :target="channel.icon === 'github' ? '_blank' : undefined"
          :rel="channel.icon === 'github' ? 'noreferrer' : undefined"
          :aria-label="channel.icon === 'rss' ? 'RSS 订阅' : channel.label"
        >
          <AboutChannelIcon :name="channel.icon" /><span><strong>{{ channel.label }}</strong><small>{{ channel.note }}</small></span><b aria-hidden="true"><NavigationArrow direction="up-right" /></b>
        </a>
      </nav>
    </section>
  </div>
</template>

<script setup lang="ts">
import SectionHeading from '~/components/SectionHeading.vue'
import GeometricMark from '~/components/GeometricMark.vue'

import PageHeroArtwork from '~/components/PageHeroArtwork.vue'
import '~/assets/css/about-editorial.css'
import type { AboutNowStatus, AboutPageContent, ProfilePublic } from '~/types/api'

const activeCapability = ref<number | null>(null)

const props = defineProps<{
  content: AboutPageContent | null
  profile: ProfilePublic | null
}>()

const NOW_STATUS: Record<AboutNowStatus, { chip: string, label: string }> = {
  in_progress: { chip: 'chip-blue', label: 'IN_PROGRESS' },
  building: { chip: 'chip-purple', label: 'BUILDING' },
  exploring: { chip: 'chip-amber', label: 'EXPLORING' },
}

const channels = computed(() => {
  const profile = props.profile
  return [
    ...(profile?.github_url ? [{ icon: 'github' as const, label: 'GitHub', note: 'Code & Repos', href: profile.github_url }] : []),
    ...(profile?.email ? [{ icon: 'email' as const, label: 'Email', note: 'Direct Inbox', href: `mailto:${profile.email}` }] : []),
    { icon: 'rss' as const, label: 'RSS', note: 'Feed Subscription', href: '/rss.xml' },
  ]
})

</script>

<style scoped>
.about-editorial .capability-icon {display:grid;place-items:center;width:48px;height:48px;margin:0 0 20px;border:1px solid color-mix(in srgb,var(--ee-primary) 25%,var(--ee-line));border-radius:12px;background:color-mix(in srgb,var(--ee-primary) 8%,var(--ee-surface));color:var(--ee-primary-strong);}
.capability-icon svg {width:26px;height:26px;}
.capability-icon {position:relative;}
.capability-icon::after {content:'';position:absolute;left:8px;right:8px;bottom:-7px;height:2px;background:var(--ee-primary);transform:scaleX(0);transform-origin:left center;}
@media(hover:hover) and (pointer:fine) {
  .ae-domain:hover .capability-icon {background:color-mix(in srgb,var(--ee-primary) 14%,var(--ee-surface));border-color:var(--ee-primary);}
  .ae-domain:hover .capability-icon::after {transform:scaleX(1);}
}
@media(hover:hover) and (pointer:fine) and (prefers-reduced-motion:no-preference) {
  .capability-icon::after {transition:transform var(--ee-motion-fast) cubic-bezier(0.23,1,0.32,1);}
}
/* Keep the copy on one rhythm; the illustration must not size its text rows. */
.about-editorial .ae-introduction {grid-template-columns:minmax(0,1fr) minmax(320px,380px);gap:clamp(32px,5vw,72px);align-items:start;max-width:1040px;margin-inline:auto;}
.about-signature-intro {min-width:0;display:flex;flex-direction:column;align-items:flex-start;gap:16px;padding-top:4px;}
.about-editorial .about-signature-intro h1 {font-size:clamp(30px,3vw,42px);line-height:1.35;margin:0;padding-bottom:8px;}
.about-page-intro {font-size:16px;line-height:1.8;color:var(--ee-ink-muted);margin:0;max-width:28em;}
.about-signature-intro :deep(.page-artwork) {width:clamp(220px,22vw,280px);max-width:80%;padding:12px 0;margin:4px 0 0;align-self:center;}
.ae-profile-card :deep(.profile-intro .sys-panel) {padding:24px;}
.ae-profile-card :deep(.profile-intro .profile-avatar) {width:64px;height:64px;}
.ae-profile-card :deep(.profile-intro .sys-panel-id) {gap:16px;}
.ae-profile-card :deep(.profile-intro .sys-panel-name) {font-size:26px;}
.ae-profile-card :deep(.profile-intro .sys-panel-skills) {padding:16px 0;margin-top:20px;}
.ae-profile-card :deep(.profile-intro .sys-panel-foot) {padding-top:16px;}
@media(max-width:959px) {
  .about-editorial .ae-introduction {grid-template-columns:minmax(0,1fr);gap:28px;max-width:540px;}
  .about-signature-intro {gap:12px;padding-top:0;}
  .about-editorial .about-signature-intro h1 {font-size:32px;}
  .about-signature-intro :deep(.page-artwork) {width:220px;margin-top:4px;}
}
@media(max-width:479px) {
  .about-signature-intro :deep(.page-artwork) {width:190px;padding:8px 0;}
  .about-editorial .about-signature-intro h1 {font-size:28px;}
  .ae-profile-card :deep(.profile-intro .sys-panel) {padding:20px;}
}
</style>
