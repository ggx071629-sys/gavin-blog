<template>
  <main
    class="admin-login-shell"
    data-testid="admin-login-shell"
    :data-state="errorMessage ? 'error' : submitting ? 'submitting' : hydrated ? 'ready' : 'preparing'"
  >
    <div class="admin-login-theme">
      <AdminThemeToggle />
    </div>

    <section class="admin-login-form-stage" data-testid="admin-login-form-stage">
      <div class="admin-login-card" data-testid="admin-login-form-surface">
        <p class="studio-login-label">GAVIN STUDIO / 私人工作区</p>
        <h1 class="admin-page-title">登录写作台</h1>
        <p class="admin-page-description">继续你的写作与内容管理。</p>
        <p v-if="route.query.reason === 'password-updated'" role="status" class="mt-4">密码已更新，所有设备已退出。请使用新密码登录。</p>
        <p v-else-if="route.query.reason === 'session-expired'" role="status" class="mt-4">登录已失效，请重新登录。</p>
        <p v-else-if="route.query.reason === 'session-revoked'" role="status" class="mt-4">当前会话已退出。</p>

        <form class="admin-login-form" data-testid="admin-login-form" @submit.prevent="submit">
          <label class="admin-field admin-login-field" for="admin-username">
            <span>用户名</span>
            <input
              id="admin-username"
              v-model="username"
              data-testid="username"
              autocomplete="username"
              placeholder="输入管理员用户名"
              :aria-invalid="Boolean(errorMessage)"
              :aria-describedby="errorMessage ? 'login-error' : undefined"
            >
          </label>
          <label class="admin-field admin-login-field admin-login-password-field" for="admin-password">
            <span>密码</span>
            <input
              id="admin-password"
              v-model="password"
              data-testid="password"
              type="password"
              autocomplete="current-password"
              placeholder="输入密码"
              :aria-invalid="Boolean(errorMessage)"
              :aria-describedby="errorMessage ? 'login-error' : undefined"
            >
          </label>
          <button
            class="button-primary admin-login-submit w-full justify-center"
            data-testid="login"
            type="submit"
            :disabled="submitting || !hydrated"
            :aria-busy="submitting"
          >
            {{ submitting ? '验证中…' : hydrated ? '登录' : '正在准备…' }}
          </button>
          <p v-if="errorMessage" id="login-error" role="alert" class="admin-form-error">{{ errorMessage }}</p>
        </form>
        <p class="studio-login-private">仅限站点管理员，无公开注册入口。</p>
        <NuxtLink to="/admin/recover" class="admin-login-back">忘记密码</NuxtLink>
        <NuxtLink to="/" class="admin-login-back">返回 Gavin</NuxtLink>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
definePageMeta({ layout: false })
const username = ref('gavin')
const password = ref('')
const route = useRoute()
const submitting = ref(false)
const errorMessage = ref('')
const hydrated = ref(false)

onMounted(() => {
  hydrated.value = true
})

const submit = async () => {
  if (submitting.value || !hydrated.value) return
  submitting.value = true
  errorMessage.value = ''
  try {
    const issued = await apiFetch<{ csrf_token: string }>('/auth/csrf')
    const csrf = useCookie<string>('gavin_csrf')
    csrf.value = issued.csrf_token
    await apiFetch('/auth/login', {
      method: 'POST',
      body: { username: username.value, password: password.value },
      headers: { 'X-CSRF-Token': issued.csrf_token },
    })
    await navigateTo(safeAdminReturnTo(route.query.returnTo))
  }
  catch (error: unknown) {
    errorMessage.value = loginFailureMessage(error)
  }
  finally {
    submitting.value = false
  }
}

useSeoMeta({ title: '登录写作台', robots: 'noindex,nofollow' })
</script>
