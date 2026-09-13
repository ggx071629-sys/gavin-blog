<template>
  <form class="space-y-5" @submit.prevent="prepareSubmit">
    <label v-if="!recovery" class="field">
      <span>当前密码</span>
      <input v-model="currentPassword" type="password" autocomplete="current-password" maxlength="512" required :disabled="busy">
    </label>
    <label class="field">
      <span>新密码</span>
      <input v-model="newPassword" type="password" autocomplete="new-password" minlength="15" maxlength="128" required :disabled="busy" aria-describedby="password-policy">
    </label>
    <p id="password-policy">使用 15–128 个字符，避免常见弱密码、重复字符及与当前密码相同。</p>
    <label class="field">
      <span>确认新密码</span>
      <input v-model="confirmation" type="password" autocomplete="new-password" minlength="15" maxlength="128" required :disabled="busy">
    </label>
    <div class="flex flex-wrap items-end gap-3">
      <label class="field min-w-0 flex-1">
        <span>邮箱验证码</span>
        <input v-model="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}" maxlength="6" required :disabled="busy">
      </label>
      <button type="button" class="button-secondary" :disabled="busy || cooldown > 0 || !mailAvailable" :aria-busy="sending" @click="sendCode">
        {{ sending ? '正在发送…' : cooldown > 0 ? `${cooldown} 秒后重发` : '发送验证码' }}
      </button>
    </div>
    <p v-if="!mailAvailable">邮件验证暂不可用，管理员可通过服务器终端恢复账号。</p>
    <p v-if="notice" role="status" aria-live="polite">{{ notice }}</p>
    <p v-if="errorMessage" role="alert" class="admin-form-error">{{ errorMessage }}</p>
    <p>密码更新后将退出所有设备，包括当前会话。</p>
    <button type="submit" class="button-primary" :disabled="busy || !challenge || !mailAvailable" :aria-busy="submitting">{{ submitting ? '正在更新…' : recovery ? '重设密码' : '修改密码' }}</button>
    <AdminDialog v-model="confirmOpen" labelledby="password-confirm-title" :close-disabled="submitting">
      <h2 id="password-confirm-title" class="text-xl font-semibold">确认更新密码并退出所有设备？</h2>
      <p class="my-5">成功后需要使用新密码重新登录。</p>
      <div class="flex flex-wrap gap-3">
        <button type="button" class="button-secondary" :disabled="submitting" @click="confirmOpen = false">取消</button>
        <button type="button" class="button-primary" :disabled="submitting" @click="submit">确认更新密码</button>
      </div>
    </AdminDialog>
  </form>
</template>

<script setup lang="ts">
import type { CodeIssued } from '~/types/account'
import { accountFailureMessage, accountRetryAfter } from '~/utils/account'

const props = withDefaults(defineProps<{ recovery?: boolean; mailAvailable?: boolean }>(), { recovery: false, mailAvailable: true })
const currentPassword = ref('')
const newPassword = ref('')
const confirmation = ref('')
const code = ref('')
const challenge = ref('')
const sending = ref(false)
const submitting = ref(false)
const busy = computed(() => sending.value || submitting.value)
const confirmOpen = ref(false)
const notice = ref('')
const errorMessage = ref('')
const cooldown = ref(0)
let retryAt = 0
let timer: ReturnType<typeof setInterval> | undefined
let disposed = false
const prefix = computed(() => props.recovery ? '/auth/recovery' : '/auth/account')
function clearSensitive() {
  currentPassword.value = newPassword.value = confirmation.value = code.value = challenge.value = ''
  confirmOpen.value = false
}
function setCooldown(seconds: number) {
  retryAt = Date.now() + seconds * 1000
  cooldown.value = seconds
}
async function csrf() {
  if (!props.recovery) return
  const issued = await apiFetch<{ csrf_token: string }>('/auth/csrf')
  useCookie<string>('gavin_csrf').value = issued.csrf_token
}
async function fail(error: unknown) {
  if (disposed) return
  errorMessage.value = accountFailureMessage(error)
  const wait = accountRetryAfter(error)
  if (wait) setCooldown(wait)
  if (apiErrorStatus(error) === 401) {
    clearSensitive()
    await navigateTo('/admin/login?reason=session-expired')
  }
}
async function sendCode() {
  if (busy.value || cooldown.value || !props.mailAvailable) return
  errorMessage.value = notice.value = ''
  if (!props.recovery && !currentPassword.value) { errorMessage.value = '请先输入当前密码。'; return }
  sending.value = true
  try {
    await csrf()
    const issued = await apiFetch<CodeIssued>(`${prefix.value}/code`, { method: 'POST', body: props.recovery ? {} : { current_password: currentPassword.value } })
    if (disposed) return
    challenge.value = issued.challenge_id
    code.value = ''
    setCooldown(issued.retry_after)
    notice.value = `已提交发送，请检查邮箱。验证码 ${Math.ceil(issued.expires_in / 60)} 分钟内有效。`
  }
  catch (error: unknown) { await fail(error) }
  finally { sending.value = false }
}
function prepareSubmit() {
  if (busy.value || !challenge.value || !props.mailAvailable) return
  errorMessage.value = ''
  if (newPassword.value !== confirmation.value) { errorMessage.value = '两次新密码输入不一致。'; return }
  confirmOpen.value = true
}
async function submit() {
  if (busy.value || !confirmOpen.value) return
  submitting.value = true
  notice.value = errorMessage.value = ''
  try {
    await csrf()
    await apiFetch(`${prefix.value}/password`, { method: 'POST', body: {
      new_password: newPassword.value, challenge_id: challenge.value, code: code.value,
      ...(props.recovery ? {} : { current_password: currentPassword.value }),
    } })
    clearSensitive()
    if (!disposed) await navigateTo('/admin/login?reason=password-updated')
  }
  catch (error: unknown) { confirmOpen.value = false; await fail(error) }
  finally { submitting.value = false }
}
onMounted(() => { timer = setInterval(() => { cooldown.value = Math.max(0, Math.ceil((retryAt - Date.now()) / 1000)) }, 1000) })
onBeforeUnmount(() => { disposed = true; clearInterval(timer); clearSensitive() })
</script>
