<template>
  <section :id="`taxonomy-${kind}`" :data-testid="`taxonomy-${kind}`" class="taxonomy-manager">
    <div>
      <h2 class="text-xl font-semibold">{{ title }}</h2>
      <p class="taxonomy-explanation">{{ kind === 'categories' ? '每篇文章的主要归属。' : '连接不同栏目中的共同主题。' }} 已有关联的项目需先解除关联才能删除。</p>
    </div>

    <p class="mt-2 text-sm text-ee-ink-faint">共 {{ localItems.length }} 项</p>
    <div class="taxonomy-manager__workspace">
    <div class="taxonomy-manager__rows">
      <article v-for="item in localItems" :key="item.id" class="taxonomy-manager__row">
        <div>
          <h3 class="font-medium">{{ item.name }}</h3>
          <p class="mt-1 text-sm text-ee-ink-faint">{{ item.slug }}</p>
          <p v-if="item.description" class="mt-1 text-sm text-ee-ink-faint">{{ item.description }}</p>
        </div>
        <div class="flex gap-3 text-sm">
          <button type="button" class="admin-inline-action" :disabled="submitting || checking" @click="edit(item)">编辑</button>
          <button type="button" class="admin-inline-action text-ee-danger-ink" :disabled="submitting || checking" @click="remove(item)">删除</button>
        </div>
      </article>
      <p v-if="!localItems.length" class="py-5 text-sm text-ee-ink-faint">尚未创建。</p>
    </div>
    <form class="taxonomy-manager__form space-y-4" @submit.prevent="submit">
      <p class="text-sm font-semibold">{{ editingId ? `编辑${title}` : `新建${title}` }}</p>
      <label class="field">
        <span>名称</span>
        <input ref="nameInput" v-model="form.name" :data-testid="`${kind}-name`" maxlength="80" required @input="syncSlug">
      </label>
      <label class="field">
        <span>链接标识（Slug）</span>
        <input v-model="form.slug" :data-testid="`${kind}-slug`" maxlength="80" required @input="slugTouched = true">
      </label>
      <label class="field">
        <span>说明</span>
        <input v-model="form.description" maxlength="240">
      </label>
      <p v-if="errorMessage" role="alert" class="text-sm text-ee-danger-ink">{{ errorMessage }}</p>
      <p v-if="statusMessage" role="status" class="text-sm text-ee-ink-faint">{{ statusMessage }}</p>
      <button v-if="needsReview" type="button" class="button-secondary" :disabled="submitting || checking" @click="checkLatest">
        {{ checking ? '核对中…' : '核对最新列表' }}
      </button>
      <div class="flex items-center justify-end gap-3">
        <button v-if="editingId" type="button" class="button-secondary" :disabled="submitting || checking" @click="reset">取消编辑</button>
        <button class="button-primary" :data-testid="`${kind}-submit`" :disabled="submitting || checking">
          {{ submitting ? '保存中…' : editingId ? '保存修改' : `新建${title}` }}
        </button>
      </div>
    </form>

    </div>
  </section>
</template>

<script setup lang="ts">
import type { TaxonomyItem } from '~/types/api'
import { slugify } from '~/utils/article'

const props = defineProps<{
  kind: 'categories' | 'tags'
  title: string
  items: TaxonomyItem[]
}>()
const nameInput = ref<HTMLInputElement | null>(null)
const localItems = ref([...props.items])
const editingId = ref<number | null>(null)
const slugTouched = ref(false)
const submitting = ref(false)
const checking = ref(false)
const needsReview = ref(false)
const errorMessage = ref('')
const statusMessage = ref('')
const form = reactive({ name: '', slug: '', description: '' })

// This is a local UI wait budget, not a guarantee that an aborted write rolled back.
const REQUEST_WAIT_MS = 15_000
class TaxonomyRequestTimeout extends Error {}
let activeController: AbortController | undefined
let disposed = false
onBeforeUnmount(() => {
  disposed = true
  activeController?.abort()
})

async function request<T>(endpoint: string, options: { method: 'GET' | 'POST' | 'PATCH' | 'DELETE'; body?: object }): Promise<T> {
  const controller = new AbortController()
  activeController = controller
  let timer: ReturnType<typeof setTimeout> | undefined
  const deadline = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      reject(new TaxonomyRequestTimeout())
      controller.abort()
    }, REQUEST_WAIT_MS)
  })
  try {
    return await Promise.race([
      apiFetch<T>(endpoint, { ...options, signal: controller.signal, retry: 0 }),
      deadline,
    ])
  }
  finally {
    clearTimeout(timer)
    if (activeController === controller) activeController = undefined
  }
}

const checkLatest = async () => {
  if (submitting.value || checking.value) return
  checking.value = true
  statusMessage.value = ''
  try {
    const items = await request<TaxonomyItem[]>(`/admin/${props.kind}`, { method: 'GET' })
    if (disposed) return
    localItems.value = items
    errorMessage.value = ''
    statusMessage.value = '列表已更新，请核对结果后再决定是否提交。当前输入仍保留。'
  }
  catch (error) {
    if (disposed) return
    errorMessage.value = error instanceof TaxonomyRequestTimeout
      ? '核对超时，操作结果仍未确认。输入已保留，请稍后再次核对。'
      : '暂时无法核对最新列表。操作结果仍未确认，输入已保留。'
  }
  finally { if (!disposed) checking.value = false }
}

const syncSlug = () => {
  if (!slugTouched.value) form.slug = slugify(form.name)
}

const reset = () => {
  editingId.value = null
  slugTouched.value = false
  errorMessage.value = ''
  statusMessage.value = ''
  needsReview.value = false
  Object.assign(form, { name: '', slug: '', description: '' })
}

const edit = async (item: TaxonomyItem) => {
  errorMessage.value = ''
  editingId.value = item.id
  slugTouched.value = true
  Object.assign(form, {
    name: item.name,
    slug: item.slug,
    description: item.description,
  })
  await nextTick()
  nameInput.value?.focus()
}

const submit = async () => {
  if (submitting.value || checking.value) return
  submitting.value = true
  errorMessage.value = ''
  statusMessage.value = ''
  try {
    const endpoint = `/admin/${props.kind}` + (editingId.value ? `/${editingId.value}` : '')
    const saved = await request<TaxonomyItem>(endpoint, {
      method: editingId.value ? 'PATCH' : 'POST',
      body: { ...form },
    })
    if (disposed) return
    const index = localItems.value.findIndex(item => item.id === saved.id)
    if (index === -1) localItems.value.push(saved)
    else localItems.value[index] = saved
    localItems.value.sort((left, right) => left.name.localeCompare(right.name, 'zh-CN'))
    reset()
  }
  catch (error) {
    if (disposed) return
    if (error instanceof TaxonomyRequestTimeout) {
      needsReview.value = true
      errorMessage.value = '等待已超时，保存结果尚未确认。输入已保留，请先核对最新列表，避免重复提交。'
    }
    else errorMessage.value = '保存失败。请检查名称和 slug 是否有效或重复。'
  }
  finally {
    if (!disposed) submitting.value = false
  }
}

const remove = async (item: TaxonomyItem) => {
  if (submitting.value || checking.value) return
  if (!window.confirm(`确定删除“${item.name}”吗？已被文章使用的项目无法删除。`)) return
  submitting.value = true
  errorMessage.value = ''
  statusMessage.value = ''
  try {
    await request(`/admin/${props.kind}/${item.id}`, { method: 'DELETE' })
    if (disposed) return
    localItems.value = localItems.value.filter(current => current.id !== item.id)
    if (editingId.value === item.id) reset()
  }
  catch (error) {
    if (disposed) return
    if (error instanceof TaxonomyRequestTimeout) {
      needsReview.value = true
      errorMessage.value = '等待已超时，删除结果尚未确认。请核对最新列表后再决定是否重试。'
    }
    else errorMessage.value = '无法删除：该项目可能仍被文章使用，或服务暂不可用。请检查后重试。'
  }
  finally { if (!disposed) submitting.value = false }
}
</script>

<style scoped>
.taxonomy-manager { scroll-margin-top: 24px; border-top: 0; padding-block: 28px; }
.taxonomy-manager h2 { font-size: 22px; }
.taxonomy-explanation { color: var(--studio-muted); margin-top: 12px; line-height: 1.7; }
.taxonomy-manager__workspace { grid-template-columns: minmax(0, 1fr) minmax(280px, .65fr); gap: 36px; }
.taxonomy-manager__form { border: 0; border-radius: 0; padding: 0 0 0 24px; border-left: 1px solid var(--studio-divider); background: none; }
.taxonomy-manager__row { padding-block: 22px; }
.taxonomy-manager__row h3 { font-size: 18px; }
@media (max-width: 1000px) {
  .taxonomy-manager__workspace { grid-template-columns: minmax(0, 1fr); }
  .taxonomy-manager__form { padding: 24px 0 0; border-left: 0; border-top: 1px solid var(--studio-divider); }
}
</style>
