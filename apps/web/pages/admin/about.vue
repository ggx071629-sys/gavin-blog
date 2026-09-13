<template>
  <section v-if="!isChild && page" class="resource-ops resource-ops--about space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight">关于页内容</h1>
        <p class="mt-1 text-sm text-ee-ink-faint">
          整理个人经历、近期方向和写作范围。身份与联系由个人名片统一维护。
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-3">
        <span class="save-state" :data-state="saveState" aria-live="polite">{{ stateLabel }}</span>
        <button type="button" class="button-secondary" data-testid="about-preview-open" @click="openPreview">预览草稿</button>
        <NuxtLink class="button-secondary" to="/admin/about/revisions">版本历史</NuxtLink>
        <NuxtLink class="button-secondary" to="/about" target="_blank">查看公开页</NuxtLink>
        <button
          type="button"
          class="button-primary"
          data-testid="about-publish"
          :disabled="publishing || saveState === 'conflict'"
          @click="publish"
        >
          {{ publishing ? '发布中…' : page.status === 'published' ? '更新发布' : '发布' }}
        </button>
      </div>
    </div>

    <div
      v-if="saveState === 'conflict'"
      role="alert"
      class="rounded-ee-soft border border-ee-warning-border bg-ee-warning-bg p-4 text-sm text-ee-warning-ink dark:border-ee-warning-border dark:bg-ee-warning-bg dark:text-ee-warning-ink"
      data-testid="about-conflict"
    >
      服务器上已有更新。为避免覆盖，请
      <button type="button" class="font-semibold underline" data-testid="about-refresh" @click="reload">刷新页面</button>
      后重新合并。
    </div>
    <div v-if="errorMessage" role="alert" class="rounded-ee-soft border border-ee-danger-border bg-ee-danger-bg p-4 text-sm text-ee-danger-ink dark:border-ee-danger-border dark:bg-ee-danger-bg dark:text-ee-danger-ink">
      {{ errorMessage }}
    </div>

    <p class="about-publication-state" role="status" data-testid="about-publication-state">
      {{ page.status === 'published' ? `当前公开：修订 #${page.current_publish_revision}` : '尚未公开' }}
      <span v-if="page.has_unpublished_changes"> · 有未发布修改</span>
      <span> · 草稿自动保存，发布后才更新公开内容。</span>
    </p>
    <div class="ops-panel about-identity flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2>身份与联系</h2>
        <p>姓名、头像、定位、技能与联系渠道继续由个人名片提供，改动会同步首页。</p>
      </div>
      <NuxtLink class="button-secondary" to="/admin/profile">前往个人名片</NuxtLink>
    </div>

    <div class="grid gap-6">
      <section class="ops-panel" aria-labelledby="about-statement-title">
        <h2 id="about-statement-title">引言</h2>
        <label class="field mt-4">
          <span>引言文字</span>
          <textarea v-model="form.statement" data-testid="about-statement" rows="3" maxlength="500" />
        </label>
      </section>

      <section class="ops-panel" aria-labelledby="about-capabilities-title">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 id="about-capabilities-title">能力领域（{{ form.capabilities.length }} / {{ ABOUT_CARD_LIMIT }}）</h2>
            <p>每项含标题、描述与标签；公开页按顺序渲染为领域卡片。</p>
          </div>
          <button type="button" class="button-secondary" data-testid="about-capability-add" :disabled="form.capabilities.length >= ABOUT_CARD_LIMIT" @click="addCapability">
            添加领域
          </button>
        </div>
        <div class="mt-5 grid gap-4">
          <article
            v-for="(capability, index) in form.capabilities"
            :key="index"
            class="rounded-ee-soft border border-ee-line bg-ee-surface-low p-4 dark:border-ee-line dark:bg-ee-surface-low"
            data-testid="about-capability-card"
          >
              <div class="mb-3 flex items-center justify-between gap-3">
                <span class="text-sm font-semibold uppercase tracking-[0.16em] text-ee-ink-faint">领域 {{ index + 1 }}</span>
                <div class="flex gap-1">
                <button type="button" class="button-secondary px-2" :disabled="index === 0" data-testid="about-capability-up" aria-label="上移条目" @click="moveCapability(index, -1)">上移</button>
                <button type="button" class="button-secondary px-2" :disabled="index === form.capabilities.length - 1" data-testid="about-capability-down" aria-label="下移条目" @click="moveCapability(index, 1)">下移</button>
                <button type="button" class="button-secondary px-2 text-ee-danger-ink" data-testid="about-capability-remove" @click="removeCapability(index)">删除</button>
              </div>
            </div>
            <div class="grid gap-4 md:grid-cols-2">
              <label class="field">
                <span>标题</span>
                <input v-model="capability.title" maxlength="80" data-testid="about-capability-title">
              </label>
              <label class="field">
                <span>描述</span>
                <textarea v-model="capability.description" rows="2" maxlength="320" data-testid="about-capability-description" />
              </label>
            </div>
            <div class="mt-3 flex flex-wrap items-center gap-2">
              <span
                v-for="(tag, tagIndex) in capability.tags"
                :key="tag"
                class="inline-flex items-center gap-1 rounded-full bg-ee-surface-high px-3 py-1 text-sm font-semibold text-ee-ink-muted dark:bg-ee-surface-high dark:text-ee-ink-muted"
              >
                {{ tag }}
                <button type="button" class="text-ee-ink-faint hover:text-ee-danger-ink" aria-label="删除领域标签" data-testid="about-tag-remove" @click="capability.tags.splice(tagIndex, 1)">×</button>
              </span>
              <span class="flex gap-1">
                <input
                  v-model="tagDrafts[index]"
                  class="min-w-0"
                  maxlength="30"
                  placeholder="标签（Enter 添加）"
                  aria-label="新增领域标签" data-testid="about-tag-input"
                  @keydown.enter.prevent="addTag(index)"
                >
                <button type="button" class="button-secondary" data-testid="about-tag-add" :disabled="!(tagDrafts[index] || '').trim() || capability.tags.length >= 6" @click="addTag(index)">添加</button>
              </span>
            </div>
          </article>
        </div>
      </section>

      <section class="ops-panel" aria-labelledby="about-now-title">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 id="about-now-title">最近在做（{{ form.now.length }} / {{ ABOUT_CARD_LIMIT }}）</h2>
            <p>每条跳转到站内文章、项目或读书列表。</p>
          </div>
          <button type="button" class="button-secondary" data-testid="about-now-add" :disabled="form.now.length >= ABOUT_CARD_LIMIT" @click="addNow">添加条目</button>
        </div>
        <div v-if="form.now.length" class="mt-5 grid gap-4">
          <article
            v-for="(item, index) in form.now"
            :key="index"
            class="grid gap-4 rounded-ee-soft border border-ee-line bg-ee-surface-low p-4 dark:border-ee-line dark:bg-ee-surface-low md:grid-cols-[1fr_180px_180px_auto]"
            data-testid="about-now-card"
          >
            <label class="field">
              <span>文字</span>
              <input v-model="item.label" maxlength="80" data-testid="about-now-label">
            </label>
            <label class="field">
              <span>状态</span>
              <select v-model="item.status" data-testid="about-now-status">
                <option value="in_progress">进行中</option>
                <option value="building">构建中</option>
                <option value="exploring">探索中</option>
              </select>
            </label>
            <label class="field">
              <span>目标</span>
              <select v-model="item.target" data-testid="about-now-target">
                <option value="projects">项目</option>
                <option value="articles">文章</option>
                <option value="books">读书</option>
              </select>
            </label>
            <div class="flex items-end gap-1">
              <button type="button" class="button-secondary px-2" :disabled="index === 0" data-testid="about-now-up" aria-label="上移条目" @click="moveItem(form.now, index, -1)">上移</button>
              <button type="button" class="button-secondary px-2" :disabled="index === form.now.length - 1" data-testid="about-now-down" aria-label="下移条目" @click="moveItem(form.now, index, 1)">下移</button>
              <button type="button" class="button-secondary px-2 text-ee-danger-ink" data-testid="about-now-remove" @click="form.now.splice(index, 1)">删除</button>
            </div>
          </article>
        </div>
      </section>

      <section class="ops-panel" aria-labelledby="about-editorial-title">
        <h2 id="about-editorial-title">写作范围</h2>
        <p class="mb-4">公开页按顺序用“•”连接这些主题。</p>
        <div class="flex flex-wrap items-center gap-2">
          <span
            v-for="(topic, index) in form.editorial_topics"
            :key="topic"
            class="inline-flex items-center gap-1 rounded-full bg-ee-surface-high px-3 py-1 text-sm font-semibold text-ee-ink-muted dark:bg-ee-surface-high dark:text-ee-ink-muted"
          >
            {{ topic }}
            <button type="button" class="text-ee-ink-faint hover:text-ee-danger-ink" aria-label="删除写作主题" data-testid="about-topic-remove" @click="form.editorial_topics.splice(index, 1)">×</button>
          </span>
          <span class="flex gap-1">
            <input v-model="topicDraft" maxlength="40" placeholder="主题（Enter 添加）" aria-label="新增写作主题" data-testid="about-topic-input" @keydown.enter.prevent="addTopic">
            <button type="button" class="button-secondary" data-testid="about-topic-add" :disabled="!topicDraft.trim() || form.editorial_topics.length >= 8" @click="addTopic">添加</button>
          </span>
        </div>
      </section>

      <section class="ops-panel" aria-labelledby="about-site-title">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 id="about-site-title">网站说明与技术栈</h2>
            <p>“关于这个网站”段落与公开站点规格条目。</p>
          </div>
          <button type="button" class="button-secondary" data-testid="about-stack-add" :disabled="form.site.stack.length >= 8" @click="form.site.stack.push({ label: '', value: '' })">
            添加规格
          </button>
        </div>
        <label class="field mt-4">
          <span>说明</span>
          <textarea v-model="form.site.description" rows="3" maxlength="320" data-testid="about-site-description" />
        </label>
        <div v-if="form.site.stack.length" class="mt-4 grid gap-3">
          <div
            v-for="(entry, index) in form.site.stack"
            :key="index"
            class="grid items-end gap-3 rounded-ee-soft border border-ee-line bg-ee-surface-low p-3 dark:border-ee-line dark:bg-ee-surface-low md:grid-cols-[200px_1fr_auto]"
            data-testid="about-stack-row"
          >
            <label class="field"><span>标签</span><input v-model="entry.label" maxlength="40" data-testid="about-stack-label"></label>
            <label class="field"><span>值</span><input v-model="entry.value" maxlength="80" data-testid="about-stack-value"></label>
            <button type="button" class="button-secondary px-2 text-ee-danger-ink" data-testid="about-stack-remove" @click="form.site.stack.splice(index, 1)">删除</button>
          </div>
        </div>
      </section>
    </div>
  </section>
  <NuxtPage v-else-if="isChild" />
</template>

<script setup lang="ts">
import '~/assets/css/resource-operations.css'
import type { AboutPageAdmin, AboutPageContent } from '~/types/api'
import { AutosaveQueue } from '~/utils/autosave'
import { useAutosaveSafety } from '~/composables/useAutosaveSafety'
import { apiErrorDetail, isOptimisticLockConflict } from '~/utils/api-errors'

definePageMeta({ layout: 'admin-core', middleware: 'admin' })
useSeoMeta({ title: '关于页内容' })

const route = useRoute()
const ABOUT_CARD_LIMIT = 10
const isChild = computed(() => route.path.startsWith('/admin/about/'))

const { data: page, refresh, error } = await useAsyncData<AboutPageAdmin>(
  'admin-about-page',
  () => apiFetch<AboutPageAdmin>('/admin/about-page'),
)
useApiFailure(error)

const form = reactive<AboutPageContent>(emptyContent())
const tagDrafts = ref<string[]>([])
const topicDraft = ref('')
const loaded = ref(false)
const skipDirty = ref(false)
const saveState = ref<'idle' | 'pending' | 'saving' | 'saved' | 'error' | 'conflict'>('idle')
const publishing = ref(false)
const errorMessage = ref('')

const stateLabel = computed(() => ({
  idle: '尚未修改',
  pending: '等待保存',
  saving: '保存中…',
  saved: '工作副本已保存',
  error: '保存失败',
  conflict: '内容冲突',
})[saveState.value])

function emptyContent(): AboutPageContent {
  return {
    statement: '',
    capabilities: [],
    now: [],
    editorial_topics: [],
    site: { description: '', stack: [] },
  }
}

const assignForm = (content: AboutPageContent) => {
  form.statement = content.statement
  form.capabilities = content.capabilities.map(item => ({
    title: item.title,
    description: item.description,
    tags: [...item.tags],
  }))
  form.now = content.now.map(item => ({ ...item }))
  form.editorial_topics = [...content.editorial_topics]
  form.site = {
    description: content.site.description,
    stack: content.site.stack.map(item => ({ ...item })),
  }
}

// 服务器工作副本刷新（首次加载、刷新、发布）重建草稿；
// 自动保存回声只同步已提交字段，保留正在输入但尚未提交的标签。
const syncFromServer = (content: AboutPageContent, resetDrafts: boolean) => {
  assignForm(content)
  if (resetDrafts) {
    tagDrafts.value = content.capabilities.map(() => '')
    return
  }
  const drafts = tagDrafts.value.slice(0, content.capabilities.length)
  while (drafts.length < content.capabilities.length) drafts.push('')
  tagDrafts.value = drafts
}

const pendingEcho = ref(0)

watch(page, (value) => {
  if (!value) return
  const isSaveEcho = pendingEcho.value > 0
  if (isSaveEcho) pendingEcho.value -= 1
  skipDirty.value = true
  syncFromServer(value.content, !isSaveEcho)
  loaded.value = true
  nextTick(() => { skipDirty.value = false })
}, { immediate: true })

const cloneContent = (): AboutPageContent => JSON.parse(JSON.stringify(form)) as AboutPageContent

const save = async (snapshot: AboutPageContent) => {
  if (!page.value) throw new Error('关于页尚未加载')
  const updated = await apiFetch<AboutPageAdmin>('/admin/about-page', {
    method: 'PATCH',
    body: { content: snapshot, version: page.value.version },
  })
  pendingEcho.value += 1
  page.value = updated
}

const queue = new AutosaveQueue(save, state => {
  saveState.value = state
})

watch(form, () => {
  if (!loaded.value || skipDirty.value) return
  queue.schedule(cloneContent())
}, { deep: true })

const { flushBeforeNavigation } = useAutosaveSafety(queue, (saveError) => {
  errorMessage.value = apiErrorDetail(saveError) || '保存失败，请稍后重试。'
})

const addCapability = () => {
  if (form.capabilities.length >= ABOUT_CARD_LIMIT) return
  form.capabilities.push({ title: '', description: '', tags: [] })
  tagDrafts.value.push('')
}
const removeCapability = (index: number) => {
  form.capabilities.splice(index, 1)
  tagDrafts.value.splice(index, 1)
}
const moveCapability = (index: number, delta: number) => {
  moveItem(form.capabilities, index, delta)
  moveItem(tagDrafts.value, index, delta)
}
const addTag = (index: number) => {
  const value = (tagDrafts.value[index] || '').trim()
  const capability = form.capabilities[index]
  if (!value || !capability || capability.tags.length >= 6) return
  capability.tags.push(value)
  tagDrafts.value[index] = ''
}
const addNow = () => {
  if (form.now.length >= ABOUT_CARD_LIMIT) return
  form.now.push({ label: '', status: 'in_progress', target: 'projects' })
}
const addTopic = () => {
  const value = topicDraft.value.trim()
  if (!value || form.editorial_topics.length >= 8) return
  form.editorial_topics.push(value)
  topicDraft.value = ''
}
function moveItem<T>(items: T[], index: number, delta: number): void {
  const target = index + delta
  if (target < 0 || target >= items.length) return
  const item = items[index]
  if (item === undefined) return
  items.splice(index, 1)
  items.splice(target, 0, item)
}

const publish = async () => {
  if (publishing.value || !page.value || saveState.value === 'conflict') return
  publishing.value = true
  errorMessage.value = ''
  try {
    if (!await flushBeforeNavigation()) return
    const updated = await apiFetch<AboutPageAdmin>('/admin/about-page/publish', {
      method: 'POST',
      body: { version: page.value.version },
    })
    skipDirty.value = true
    page.value = updated
    assignForm(updated.content)
    saveState.value = 'saved'
    nextTick(() => { skipDirty.value = false })
    await navigateTo('/about')
  }
  catch (publishError) {
    if (isOptimisticLockConflict(publishError)) {
      saveState.value = 'conflict'
      return
    }
    errorMessage.value = apiErrorDetail(publishError) || '发布失败，请稍后重试。'
  }
  finally {
    publishing.value = false
  }
}

const openPreview = async () => {
  if (!await flushBeforeNavigation()) return
  await navigateTo('/admin/about/preview')
}

const reload = async () => {
  await refresh()
  saveState.value = 'idle'
  errorMessage.value = ''
}

onBeforeRouteLeave(() => {
  if (saveState.value === 'error' || saveState.value === 'conflict') {
    return window.confirm('有未保存的修改或冲突，确定离开？')
  }
})
</script>

<style scoped>
.resource-ops--about { max-width: none; margin: 0; --ee-ink-faint: var(--studio-muted); }
.resource-ops--about h1 { font-size: 36px; margin: 0; }
.about-publication-state { padding-block: 18px; border-block: 1px solid var(--studio-divider); color: var(--studio-muted); line-height: 1.7; }
.resource-ops--about .ops-panel { border: 0; border-bottom: 1px solid var(--studio-divider); border-radius: 0; background: none; padding: 28px 0; }
.resource-ops--about section.ops-panel { display: grid; grid-template-columns: minmax(180px, .42fr) minmax(0, 1fr); column-gap: 36px; align-items: start; }
.resource-ops--about section.ops-panel > :first-child { grid-column: 1; grid-row: 1 / span 6; }
.resource-ops--about section.ops-panel > :not(:first-child) { grid-column: 2; margin-top: 0; margin-bottom: 20px; min-width: 0; }
.resource-ops--about section.ops-panel > div:first-child { display: block; }
.resource-ops--about section.ops-panel > div:first-child button { margin-top: 20px; }
.resource-ops--about .ops-panel h2 { font-size: 22px; line-height: 1.5; }
.resource-ops--about .ops-panel article { min-width: 0; background: none; border: 0; border-bottom: 1px solid var(--studio-divider); border-radius: 0; padding: 0 0 24px; }
.resource-ops--about [data-testid="about-now-card"] { grid-template-columns: minmax(0, 1fr); }
.resource-ops--about [data-testid="about-stack-row"] { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto; background: none; border: 0; padding-inline: 0; }
.resource-ops--about :is([data-testid="about-tag-remove"], [data-testid="about-topic-remove"]) { min-width: 44px; min-height: 44px; }
@media (max-width: 1100px) {
  .resource-ops--about section.ops-panel { display: block; }
  .resource-ops--about section.ops-panel > :first-child { margin-bottom: 24px; }
}
@media (max-width: 760px) {
  .resource-ops--about h1 { font-size: 28px; }
  .resource-ops--about [data-testid="about-stack-row"] { grid-template-columns: minmax(0, 1fr); }
}
</style>
