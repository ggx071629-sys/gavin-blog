<template>
  <aside data-testid="profile-card" :class="{ 'profile-intro': variant === 'intro' }">
    <div data-focus-card class="sys-panel">
      <div v-if="variant !== 'intro'" class="sys-panel-sig" aria-hidden="true" />
      <div v-if="variant !== 'intro'" class="sys-panel-head">
        <span class="ee-label text-[var(--ee-accent-text)]">SYS.STATUS / Operator</span>
        <span class="sys-live" title="在线"><span class="sys-live-dot" aria-hidden="true" />Live</span>
      </div>

      <div class="sys-panel-id">
        <img
          v-if="profile.avatar_url && !avatarFailed"
          :src="avatarSrc"
          :alt="profile.name"
          width="96"
          height="96"
          class="profile-avatar shrink-0"
          data-testid="profile-avatar"
          @error="avatarFailed = true"
        >
        <div v-else class="profile-avatar profile-avatar-fallback shrink-0" data-testid="profile-avatar" aria-hidden="true">
          {{ initial }}
        </div>
        <div class="min-w-0">
          <h2 class="sys-panel-name"><NuxtLink v-if="variant === 'intro'" to="/about">{{ profile.name }}</NuxtLink><template v-else>{{ profile.name }}</template></h2>
          <div class="profile-identity-details mt-1.5 flex flex-wrap items-center gap-1.5">
            <span class="profile-role telemetry-pill text-[var(--ee-ink)]">{{ profile.title }}</span>
            <span v-if="profile.city" class="profile-location telemetry-pill" data-testid="profile-city">{{ profile.city }}</span>
          </div>
        </div>
      </div>

      <p v-if="profile.bio" class="sys-panel-bio">
        {{ profile.bio }}
      </p>

      <section v-if="profile.skills?.length" class="sys-panel-skills" aria-labelledby="profile-skills-title">
        <h3 id="profile-skills-title" class="eyebrow">{{ variant === 'intro' ? '技术栈' : 'Core skills' }}</h3>
        <ul class="mt-3 flex flex-wrap gap-1.5" data-testid="profile-skills">
          <li
            v-for="skill in profile.skills.slice(0, 6)"
            :key="skill"
            class="rounded border bg-[var(--ee-surface-low)] px-2.5 py-1 font-mono text-sm font-semibold text-[var(--ee-ink)] transition-colors hover:border-[var(--ee-primary)]"
            style="border-color: var(--ee-line-soft)"
            data-testid="profile-skill"
          >
            {{ skill }}
          </li>
        </ul>
      </section>

      <div class="sys-panel-foot">
        <a
          v-if="profile.github_url"
          :href="interactive ? profile.github_url : undefined"
          target="_blank"
          rel="noopener noreferrer"
          class="button-secondary gap-2"
          aria-label="GitHub"
          data-testid="profile-github"
          @click="interactive ? undefined : $event.preventDefault()"
        >
          <svg class="size-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3.3-.4 6.8-1.6 6.8-7A5.4 5.4 0 0 0 19.4 4 5 5 0 0 0 19.3.5S18.2.1 15 1.8a12.3 12.3 0 0 0-6 0C5.8.1 4.7.5 4.7.5A5 5 0 0 0 4.6 4a5.4 5.4 0 0 0-1.4 3.7c0 5.4 3.5 6.6 6.8 7A4.8 4.8 0 0 0 9 18v4" stroke-linecap="round" stroke-linejoin="round" />
            <path d="M9 19c-3 .9-3-1.5-4.2-2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          <span>GitHub</span>
        </a>
        <button
          v-if="profile.email"
          type="button"
          class="button-secondary gap-2"
          :aria-label="copyState === 'copied' ? '邮箱已复制' : '复制邮箱'"
          :title="profile.email"
          data-testid="profile-email"
          @click="copyEmail"
        >
          <svg class="size-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            <rect x="3" y="5" width="18" height="14" rx="2" />
            <path d="m3 7 9 6 9-6" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          <span>{{ copyState === 'copied' ? '邮箱已复制' : '复制邮箱' }}</span>
        </button>
        <a
          v-if="profile.website_url"
          :href="interactive ? profile.website_url : undefined"
          target="_blank"
          rel="noopener noreferrer"
          class="button-secondary col-span-full gap-2"
          aria-label="个人网页"
          data-testid="profile-website"
          @click="interactive ? undefined : $event.preventDefault()"
        >
          <svg class="size-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            <circle cx="12" cy="12" r="9" />
            <path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" stroke-linecap="round" />
          </svg>
          <span>个人网页</span>
        </a>
        <a
          v-if="profile.resume_url"
          :href="interactive ? profile.resume_url : undefined"
          target="_blank"
          rel="noopener noreferrer"
          class="button-primary col-span-full gap-2"
          data-testid="profile-resume"
          @click="interactive ? undefined : $event.preventDefault()"
        >
          <svg class="size-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            <path d="M12 3v12m0 0 4-4m-4 4-4-4M5 19h14" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          <span>查看简历</span>
        </a>
      </div>
    </div>
    <div v-if="variant !== 'intro'" class="ee-ruler mt-3 hidden lg:block" aria-hidden="true" />

    <p v-if="copyState === 'failed'" class="mt-3 text-sm text-[var(--ee-danger)]" data-testid="profile-copy-failed">
      复制失败，请手动选择邮箱：<span class="font-medium">{{ profile.email }}</span>
    </p>
    <span class="sr-only" aria-live="polite" data-testid="profile-copy-feedback">{{ copyAnnouncement }}</span>
  </aside>
</template>

<script setup lang="ts">
import type { ProfilePublic } from '~/types/api'
import { resolvePublicUrl } from '~/utils/api-url'

const props = withDefaults(defineProps<{
  profile: ProfilePublic
  interactive?: boolean
  variant?: 'card' | 'intro'
}>(), { interactive: true, variant: 'card' })

const avatarFailed = ref(false)
const copyState = ref<'idle' | 'copied' | 'failed'>('idle')
let resetTimer: ReturnType<typeof setTimeout> | null = null
const initial = computed(() => props.profile.name.trim().charAt(0).toUpperCase() || 'G')
const avatarSrc = computed(() => props.profile.avatar_url ? resolvePublicUrl(props.profile.avatar_url) : '')

watch(() => props.profile.avatar_url, () => { avatarFailed.value = false })

const copyAnnouncement = computed(() => {
  if (copyState.value === 'copied') return '已复制'
  if (copyState.value === 'failed') return '复制失败，请手动复制邮箱'
  return ''
})

const copyEmail = async () => {
  if (!props.interactive || !props.profile.email) return
  if (resetTimer) clearTimeout(resetTimer)
  try {
    if (!navigator.clipboard?.writeText) throw new Error('clipboard api unavailable')
    await navigator.clipboard.writeText(props.profile.email)
    copyState.value = 'copied'
  }
  catch {
    copyState.value = 'failed'
  }
  resetTimer = setTimeout(() => { copyState.value = 'idle' }, 2000)
}

onBeforeUnmount(() => {
  if (resetTimer) clearTimeout(resetTimer)
})
</script>

<style scoped>
.profile-intro .sys-panel-foot .button-primary {
  background: var(--ee-primary);
  color: var(--ee-primary-contrast);
}

.profile-intro .sys-panel-foot .button-primary:hover {
  background: var(--ee-primary-strong);
}
</style>
