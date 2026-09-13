<template>
  <div class="space-y-5" :aria-busy="loading || revoking">
    <div class="flex flex-wrap gap-3">
      <button class="button-secondary" type="button" :disabled="loading || revoking" @click="load">刷新会话</button>
      <button class="button-secondary" type="button" :disabled="loading || revoking || !items.some(item => !item.is_current)" @click="pending = 'others'">退出其他会话</button>
    </div>
    <p v-if="loading" role="status">正在读取登录会话…</p>
    <p v-if="errorMessage" role="alert" class="admin-form-error">{{ errorMessage }}</p>
    <p v-if="notice" role="status">{{ notice }}</p>
    <p v-if="loaded && !errorMessage && !loading && !items.length">没有活跃会话。</p>
    <ul v-if="!loading && !errorMessage" class="session-list">
      <li v-for="(item, index) in items" :key="item.id" :data-testid="item.is_current ? 'current-session' : 'other-session'">
        <div class="space-y-2">
          <h3 class="font-semibold">{{ item.is_current ? '当前会话' : `登录会话 ${index + 1}` }}</h3>
          <p>登录时间：<time :datetime="item.created_at">{{ localTime(item.created_at) }}</time></p>
          <p>最近活动：<time :datetime="item.last_seen_at">{{ localTime(item.last_seen_at) }}</time></p>
        </div>
        <button type="button" class="button-secondary" :disabled="revoking" :aria-label="item.is_current ? '退出当前会话' : `退出登录会话 ${index + 1}`" @click="pending = item">{{ item.is_current ? '退出当前会话' : '退出此会话' }}</button>
      </li>
    </ul>
    <AdminDialog :model-value="pending !== null" labelledby="session-confirm-title" :close-disabled="revoking" @update:model-value="value => { if (!value) pending = null }">
      <h2 id="session-confirm-title" class="text-xl font-semibold">{{ pending === 'others' ? '确认退出其他所有会话？' : '确认退出此会话？' }}</h2>
      <p class="my-5">{{ pending !== 'others' && pending?.is_current ? '当前页面将返回登录。' : '被退出的设备下次操作时需要重新登录。当前会话会保留。' }}</p>
      <div class="flex flex-wrap gap-3">
        <button type="button" class="button-secondary" :disabled="revoking" @click="pending = null">取消</button>
        <button type="button" class="button-primary" :disabled="revoking" @click="revoke">{{ revoking ? '正在退出…' : '确认退出' }}</button>
      </div>
    </AdminDialog>
  </div>
</template>

<script setup lang="ts">
import type { SessionItem, SessionList } from '~/types/account'
import { accountFailureMessage } from '~/utils/account'

const emit = defineEmits<{ expired: [] }>()
const items = ref<SessionItem[]>([])
const loading = ref(false)
const loaded = ref(false)
const revoking = ref(false)
const errorMessage = ref('')
const notice = ref('')
const pending = ref<SessionItem | 'others' | null>(null)
let disposed = false
const localTime = (value: string) => new Date(value).toLocaleString()
async function fail(error: unknown) {
  if (disposed) return
  errorMessage.value = accountFailureMessage(error)
  if (apiErrorStatus(error) === 401) {
    emit('expired')
    await navigateTo('/admin/login?reason=session-expired')
  }
}
async function load() {
  if (loading.value) return
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await apiFetch<SessionList>('/auth/sessions')
    if (!disposed) { items.value = result.items; loaded.value = true }
  }
  catch (error: unknown) { await fail(error) }
  finally { loading.value = false }
}
async function revoke() {
  if (revoking.value || !pending.value) return
  const target = pending.value
  revoking.value = true
  notice.value = errorMessage.value = ''
  try {
    await apiFetch(`/auth/sessions/${target === 'others' ? 'others' : encodeURIComponent(target.id)}`, { method: 'DELETE' })
    if (disposed) return
    pending.value = null
    if (target !== 'others' && target.is_current) {
      emit('expired')
      await navigateTo('/admin/login?reason=session-revoked')
    }
    else {
      notice.value = target === 'others' ? '其他会话已退出。' : '所选会话已退出。'
      await load()
    }
  }
  catch (error: unknown) { pending.value = null; await fail(error) }
  finally { revoking.value = false }
}
onMounted(load)
onBeforeUnmount(() => { disposed = true })
</script>

<style scoped>
.session-list li { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 20px; padding: 24px 0; border-bottom: 1px solid var(--studio-divider); }
.session-list p { color: var(--studio-muted); line-height: 1.7; }
</style>
