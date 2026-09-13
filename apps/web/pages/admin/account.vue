<template>
  <section class="resource-ops space-y-5">
    <header>
      <h1 class="text-2xl font-semibold tracking-tight">账号安全</h1>
      <p class="profile-description">管理登录凭据与已登录设备。</p>
    </header>
    <section class="profile-section" aria-labelledby="account-info-heading" :aria-busy="loading">
      <div><h2 id="account-info-heading">账号信息</h2><p>登录名和安全邮箱由服务器固定配置。</p></div>
      <div class="space-y-5">
        <p v-if="loading" role="status">正在读取账号信息…</p>
        <div v-else-if="errorMessage">
          <p role="alert" class="admin-form-error">{{ errorMessage }}</p>
          <button class="button-secondary" type="button" @click="load">重新读取</button>
        </div>
        <dl v-else-if="account" class="space-y-5">
          <div><dt>登录名</dt><dd data-testid="account-username">{{ account.username }}</dd></div>
          <div><dt>安全邮箱</dt><dd data-testid="account-email">{{ account.email_masked ?? '尚未配置' }}</dd></div>
          <div><dt>邮件验证</dt><dd>{{ account.mail_available ? '已配置' : '暂不可用，请联系服务器管理员完成配置。' }}</dd></div>
        </dl>
        <p>安全邮箱仅用于账号验证，与个人名片的公开联系邮箱无关。</p>
      </div>
    </section>
    <section v-if="account" class="profile-section" aria-labelledby="account-password-heading">
      <div><h2 id="account-password-heading">修改密码</h2><p>使用当前密码和安全邮箱验证码确认身份。</p><NuxtLink to="/admin/recover" class="button-secondary mt-3">忘记密码</NuxtLink></div>
      <AccountPasswordForm :mail-available="account.mail_available" />
    </section>
    <section class="profile-section" aria-labelledby="account-sessions-heading">
      <div><h2 id="account-sessions-heading">登录会话</h2><p>时间按当前设备时区显示。最近活动表示服务器观察到的最近一次认证请求。</p></div>
      <AccountSessions @expired="account = null" />
    </section>
  </section>
</template>

<script setup lang="ts">
import type { AccountInfo } from '~/types/account'

definePageMeta({ layout: 'admin-core', middleware: 'admin' })
const account = ref<AccountInfo | null>(null)
const loading = ref(false)
const errorMessage = ref('')
async function load() {
  if (loading.value) return
  loading.value = true
  errorMessage.value = ''
  try {
    account.value = await apiFetch<AccountInfo>('/auth/account')
  }
  catch (error: unknown) {
    account.value = null
    if (apiErrorStatus(error) === 401) {
      await navigateTo('/admin/login?reason=session-expired')
      return
    }
    errorMessage.value = '账号信息读取失败，请重试。'
  }
  finally { loading.value = false }
}
onMounted(load)
useSeoMeta({ title: '账号安全', robots: 'noindex,nofollow' })
</script>

<style scoped>
.resource-ops { max-width: none; margin: 0; }
h1 { font-size: 36px; }
.profile-description { color: var(--studio-muted); margin-top: 12px; }
.profile-section { display: grid; grid-template-columns: minmax(180px, .42fr) minmax(0, 1fr); gap: 36px; padding: 32px 0; border-bottom: 1px solid var(--studio-divider); }
.profile-section h2 { font-size: 22px; font-weight: 600; }
.profile-section p { color: var(--studio-muted); line-height: 1.7; margin-top: 12px; }
.profile-section > * { min-width: 0; overflow-wrap: anywhere; }
dt { color: var(--studio-muted); margin-bottom: 8px; }
@media (max-width: 1000px) { .profile-section { grid-template-columns: minmax(0, 1fr); gap: 24px; } }
@media (max-width: 760px) { h1 { font-size: 28px; } .profile-section { padding-block: 24px; } }
</style>
