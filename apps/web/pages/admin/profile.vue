<template>
  <section class="resource-ops resource-ops--profile space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">个人名片</h1>
        <p class="profile-description">维护首页与关于页共用的身份和联系信息。</p>
      </div>
      <div class="flex flex-wrap items-center gap-3">
        <a href="#profile-preview" class="button-secondary">查看名片</a>
        <span class="save-state" :data-state="saveState" aria-live="polite">{{ stateLabel }}</span>
        <button
          type="button"
          class="button-primary"
          data-testid="profile-save"
          :disabled="saving"
          @click="save"
        >
          {{ saving ? '保存中…' : '保存设置' }}
        </button>
      </div>
    </div>

    <div
      v-if="saveState === 'conflict'"
      role="alert"
      class="rounded-ee-soft border border-ee-warning-border bg-ee-warning-bg p-4 text-sm text-ee-warning-ink dark:border-ee-warning-border dark:bg-ee-warning-bg dark:text-ee-warning-ink"
      data-testid="profile-conflict"
    >
      服务器上已有更新。为避免覆盖，请
      <button type="button" class="font-semibold underline" data-testid="profile-refresh" @click="reload">刷新页面</button>
      后重新合并。
    </div>
    <div
      v-if="errorMessage"
      role="alert"
      class="rounded-ee-soft border border-ee-danger-border bg-ee-danger-bg p-4 text-sm text-ee-danger-ink dark:border-ee-danger-border dark:bg-ee-danger-bg dark:text-ee-danger-ink"
    >
      {{ errorMessage }}
    </div>

    <nav aria-label="名片分区" class="profile-sections"><a href="#profile-basics">基本资料</a><a href="#profile-skills">技能与联系</a></nav>
    <div v-if="form" class="editor-grid">
      <div class="space-y-5">
        <section id="profile-basics" class="profile-section" aria-labelledby="profile-basics-heading">
          <div><h2 id="profile-basics-heading">基本资料</h2><p>让访客快速知道你是谁、在做什么。</p></div>
          <div class="space-y-5">
        <label class="field">
          <span>公开名称</span>
          <input v-model="form.name" data-testid="profile-name" maxlength="80">
        </label>
        <label class="field">
          <span>职业定位</span>
          <input v-model="form.title" data-testid="profile-title" maxlength="120">
        </label>
        <label class="field">
          <span>个人简介</span>
          <textarea v-model="form.bio" data-testid="profile-bio" rows="3" maxlength="240" />
        </label>

        </div></section>
        <section class="profile-section" aria-labelledby="profile-avatar-heading"><div><h2 id="profile-avatar-heading">头像</h2><p>用于首页名片与个人介绍，留空使用字母标识。</p></div>
        <fieldset class="field">
          <legend class="sr-only">头像</legend>
          <div class="mt-2 flex min-w-0 flex-wrap items-center gap-4 sm:flex-nowrap">
            <img
              v-if="form.avatar_url && !avatarPreviewFailed"
              :src="avatarPreviewSrc"
              :alt="form.name"
              class="profile-avatar"
              data-testid="profile-avatar-preview"
              @error="avatarPreviewFailed = true"
            >
            <div v-else class="profile-avatar profile-avatar-fallback" aria-hidden="true">{{ initial }}</div>
            <input
              v-model="form.avatar_url"
              aria-label="头像图片地址"
              class="min-w-0 flex-1"
              data-testid="profile-avatar-url"
              type="url"
              placeholder="https://… 留空使用字母标识"
            >
            <button
              v-if="form.avatar_url"
              type="button"
              class="button-secondary shrink-0"
              data-testid="profile-avatar-clear"
              @click="form.avatar_url = null; avatarPreviewFailed = false"
            >移除</button>
          </div>
          <details class="mt-4"><summary class="profile-avatar-picker">选择或上传头像</summary><MediaUploader class="mt-3" @selected="selectAvatar" /></details>
        </fieldset>

        </section>
        <section id="profile-skills" class="profile-section" aria-labelledby="profile-skills-heading"><div><h2 id="profile-skills-heading">核心技能</h2><p>以少量关键词说明你的工作领域，可调整显示顺序。</p></div>
        <fieldset class="field">
          <legend>核心技能（{{ form.skills.length }} / {{ PROFILE_MAX_SKILLS }}）</legend>
          <div class="mt-2 flex flex-wrap gap-2">
            <div
              v-for="(skill, index) in form.skills"
              :key="`${skill}-${index}`"
              class="flex items-center gap-1 rounded-full bg-ee-surface-high px-2 py-1 text-sm font-semibold text-ee-ink-muted dark:bg-ee-surface-high dark:text-ee-ink-muted"
              data-testid="profile-skill-item"
            >
              <button
                type="button"
                class="inline-flex size-11 items-center justify-center text-ee-ink-faint hover:text-ee-primary-strong disabled:opacity-30"
                :disabled="index === 0"
                :data-testid="`profile-skill-up-${index}`"
                aria-label="上移技能"
                @click="moveSkill(index, -1)"
              >上移</button>
              <button
                type="button"
                class="inline-flex size-11 items-center justify-center text-ee-ink-faint hover:text-ee-primary-strong disabled:opacity-30"
                :disabled="index === form.skills.length - 1"
                :data-testid="`profile-skill-down-${index}`"
                aria-label="下移技能"
                @click="moveSkill(index, 1)"
              >下移</button>
              <span>{{ skill }}</span>
              <button
                type="button"
                class="inline-flex size-11 items-center justify-center text-ee-ink-faint hover:text-ee-danger-ink"
                :data-testid="`profile-skill-remove-${index}`"
                aria-label="删除技能"
                @click="removeSkill(index)"
              ><StudioIcon name="x" /></button>
            </div>
          </div>
          <div class="mt-2 flex gap-2">
            <input
              v-model="newSkill"
              aria-label="新增技能"
              data-testid="profile-skill-input"
              maxlength="30"
              placeholder="新增技能（最多 30 字）"
              @keydown.enter.prevent="addSkill"
            >
            <button
              type="button"
              class="button-secondary"
              data-testid="profile-skill-add"
              :disabled="form.skills.length >= PROFILE_MAX_SKILLS || !newSkill.trim()"
              @click="addSkill"
            >添加</button>
          </div>
        </fieldset>

        </section>
        <section class="profile-section" aria-labelledby="profile-contact-heading"><div><h2 id="profile-contact-heading">联系渠道</h2><p>只填写希望公开的渠道。城市和邮箱可单独设置可见性。</p></div><div class="space-y-5">
        <div class="grid gap-4 md:grid-cols-2">
          <label class="field">
            <span>城市</span>
            <input v-model="form.city" data-testid="profile-city" maxlength="80" placeholder="只填城市级信息">
          </label>
          <label class="field">
            <span>GitHub 地址</span>
            <input v-model="form.github_url" data-testid="profile-github" type="url" placeholder="https://github.com/…">
          </label>
          <label class="field">
            <span>个人网页</span>
            <input v-model="form.website_url" data-testid="profile-website" type="url" placeholder="https://…">
          </label>
          <label class="field">
            <span>公开邮箱</span>
            <input v-model="form.email" data-testid="profile-email" type="email" placeholder="gavin@example.com">
          </label>
          <label class="field">
            <span>简历地址</span>
            <input v-model="form.resume_url" data-testid="profile-resume" type="url" placeholder="https://…/resume.pdf">
          </label>
        </div>

        <ResumeSyncStatus :saved-url="savedResumeUrl" :draft-url="form.resume_url" :revision="resumeRevision" />

        <div class="flex flex-wrap gap-6">
          <label class="inline-flex items-center gap-2 text-sm font-medium text-ee-ink-muted dark:text-ee-ink-muted">
            <input v-model="form.city_visible" type="checkbox" data-testid="profile-city-visible">
            公开显示城市
          </label>
          <label class="inline-flex items-center gap-2 text-sm font-medium text-ee-ink-muted dark:text-ee-ink-muted">
            <input v-model="form.email_visible" type="checkbox" data-testid="profile-email-visible">
            公开显示邮箱
          </label>
        </div>
        </div></section>
      </div>

      <div id="profile-preview" class="preview-panel" tabindex="-1">
        <div class="mb-5 flex items-center justify-between border-b border-ee-line pb-3 dark:border-ee-line">
          <span class="text-sm font-semibold uppercase tracking-[0.18em] text-ee-ink-faint">实时预览</span>
          <span class="text-sm text-ee-ink-faint">保存后在首页与关于页更新</span>
        </div>
        <ProfileCard :profile="previewProfile" :interactive="false" />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import '~/assets/css/resource-operations.css'
import type { Profile, ProfilePublic, ProfileUpdate } from '~/types/api'
import { resolvePublicUrl } from '~/utils/api-url'
import { PROFILE_MAX_SKILLS, canAddSkill, reorderSkills } from '~/utils/profile'

definePageMeta({ layout: 'admin-core', middleware: 'admin' })
useSeoMeta({ title: '个人名片' })

const { data: profile, refresh, error: profileError } = await useAsyncData<Profile>('admin-profile', () =>
  apiFetch<Profile>('/admin/profile'),
)
useApiFailure(profileError)

const form = ref<ProfileUpdate | null>(null)
const avatarPreviewFailed = ref(false)
const newSkill = ref('')
const saving = ref(false)
const saveState = ref<'idle' | 'saved' | 'error' | 'conflict'>('idle')
const errorMessage = ref('')
const loaded = ref(false)
const dirty = ref(false)
const skipDirty = ref(false)
const savedResumeUrl = ref<string | null | undefined>(profile.value?.resume_url)
const resumeRevision = ref(0)

const initial = computed(() => form.value?.name.trim().charAt(0).toUpperCase() || 'G')

const avatarPreviewSrc = computed(() => {
  const url = form.value?.avatar_url
  if (!url) return ''
  return resolvePublicUrl(url)
})

const previewProfile = computed<ProfilePublic>(() => {
  const f = form.value!
  return {
    name: f.name || 'Gavin',
    title: f.title,
    bio: f.bio,
    skills: f.skills,
    avatar_url: f.avatar_url || undefined,
    github_url: f.github_url || undefined,
    website_url: f.website_url || undefined,
    resume_url: f.resume_url || undefined,
    city: f.city_visible && f.city ? f.city : undefined,
    email: f.email_visible && f.email ? f.email : undefined,
  }
})

const stateLabel = computed(() => ({
  idle: dirty.value ? '有未保存修改' : '尚未修改',
  saved: '个人名片已更新',
  error: '保存失败',
  conflict: '内容冲突',
})[saveState.value])

watch(profile, (value) => {
  if (!value) return
  savedResumeUrl.value = value.resume_url
  resumeRevision.value++
  skipDirty.value = true
  form.value = {
    name: value.name,
    title: value.title,
    bio: value.bio,
    skills: [...value.skills],
    avatar_url: value.avatar_url,
    city: value.city,
    city_visible: value.city_visible,
    github_url: value.github_url,
    website_url: value.website_url,
    email: value.email,
    email_visible: value.email_visible,
    resume_url: value.resume_url,
    version: value.version,
  }
  avatarPreviewFailed.value = false
  loaded.value = true
  dirty.value = false
  nextTick(() => { skipDirty.value = false })
}, { immediate: true })

watch(form, () => {
  if (loaded.value && !skipDirty.value) {
    dirty.value = true
    if (saveState.value === 'saved') saveState.value = 'idle'
  }
}, { deep: true })

const addSkill = () => {
  const value = newSkill.value.trim()
  if (!form.value || !canAddSkill(form.value.skills, value)) return
  form.value.skills.push(value)
  newSkill.value = ''
}
const removeSkill = (index: number) => form.value?.skills.splice(index, 1)
const moveSkill = (index: number, delta: number) => {
  if (!form.value) return
  form.value.skills = reorderSkills(form.value.skills, index, index + delta)
}

const selectAvatar = (url: string) => {
  if (!form.value) return
  form.value.avatar_url = url
  avatarPreviewFailed.value = false
}

const buildPayload = (): ProfileUpdate | null => {
  if (!form.value) return null
  const f = form.value
  return {
    name: f.name.trim(),
    title: f.title.trim(),
    bio: f.bio.trim(),
    skills: f.skills.map(skill => skill.trim()).filter(Boolean),
    avatar_url: f.avatar_url || null,
    city: f.city?.trim() || null,
    city_visible: f.city_visible,
    github_url: f.github_url?.trim() || null,
    website_url: f.website_url?.trim() || null,
    email: f.email?.trim() || null,
    email_visible: f.email_visible,
    resume_url: f.resume_url?.trim() || null,
    version: f.version,
  }
}

const save = async () => {
  if (!form.value || saving.value) return
  const payload = buildPayload()
  if (!payload) return
  saving.value = true
  errorMessage.value = ''
  try {
    const updated = await apiFetch<Profile>('/admin/profile', { method: 'PATCH', body: payload })
    skipDirty.value = true
    form.value = { ...form.value, ...updated, skills: [...updated.skills] }
    savedResumeUrl.value = updated.resume_url
    resumeRevision.value++
    saveState.value = 'saved'
    dirty.value = false
    nextTick(() => { skipDirty.value = false })
  }
  catch (error) {
    const status = typeof error === 'object' && error !== null && 'response' in error
      ? (error as { response?: { status?: number } }).response?.status
      : undefined
    if (status === 409) {
      saveState.value = 'conflict'
      errorMessage.value = ''
    }
    else if (status === 422) {
      saveState.value = 'error'
      errorMessage.value = '保存失败：请检查邮箱、网址格式与字段长度。'
    }
    else {
      saveState.value = 'error'
      errorMessage.value = '保存失败，请稍后重试。'
    }
  }
  finally {
    saving.value = false
  }
}

const reload = async () => {
  await refresh()
  saveState.value = 'idle'
  errorMessage.value = ''
}

onBeforeRouteLeave(() => {
  if (dirty.value && !window.confirm('有未保存的修改，确定离开？')) return false
})

const onBeforeUnload = (event: BeforeUnloadEvent) => {
  if (dirty.value) {
    event.preventDefault()
    event.returnValue = ''
  }
}
onMounted(() => window.addEventListener('beforeunload', onBeforeUnload))
onBeforeUnmount(() => window.removeEventListener('beforeunload', onBeforeUnload))
</script>

<style scoped>
.resource-ops--profile { max-width: none; margin: 0; --ee-ink-faint: var(--studio-muted); }
.resource-ops--profile h1 { font-size: 36px; margin: 0; }
.profile-description { color: var(--studio-muted); margin-top: 12px; }
.profile-sections { display: flex; gap: 18px; border-bottom: 1px solid var(--studio-divider); }
.profile-sections a { display: inline-flex; align-items: center; min-height: 54px; padding: 12px 16px; color: var(--studio-muted); }
.profile-sections a:hover { color: var(--studio-primary); background: var(--studio-low); }
.resource-ops--profile .editor-grid { display: block; }
.profile-section { display: grid; grid-template-columns: minmax(180px, .42fr) minmax(0, 1fr); gap: 36px; padding: 32px 0; border-bottom: 1px solid var(--studio-divider); scroll-margin-top: 24px; }
.resource-ops--profile .editor-grid > div:first-child { padding: 0; border: 0; border-radius: 0; background: none; box-shadow: none; }
.profile-avatar-picker { cursor: pointer; color: var(--studio-primary); min-height: 44px; padding-block: 12px; }
.profile-section h2 { font-size: 22px; font-weight: 600; }
.profile-section p { color: var(--studio-muted); line-height: 1.7; margin-top: 12px; }
.profile-section > * { min-width: 0; }
.resource-ops--profile .preview-panel { position: static; margin-top: 32px; max-width: 760px; scroll-margin-top: 24px; }
@media (max-width: 1000px) { .profile-section { grid-template-columns: minmax(0, 1fr); gap: 24px; } }
@media (max-width: 760px) { .resource-ops--profile h1 { font-size: 28px; } .profile-section { padding-block: 24px; } }
</style>
