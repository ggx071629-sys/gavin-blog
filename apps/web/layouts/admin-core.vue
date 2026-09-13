<template>
  <div class="admin-core-shell">
    <a class="skip-link" href="#admin-main">跳到主要内容</a>

    <header ref="mobileHeader" class="admin-mobile-header">
      <NuxtLink to="/admin/articles" class="admin-mobile-brand" aria-label="Gavin Studio 后台首页">
        <span>Gavin Studio</span>
      </NuxtLink>
      <div class="admin-mobile-actions">
        <AdminThemeToggle />
        <button
          ref="menuButton"
          class="admin-menu-button"
          type="button"
          aria-controls="admin-mobile-drawer"
          :aria-expanded="mobileOpen"
          :aria-label="mobileOpen ? '关闭导航菜单' : '打开导航菜单'"
          data-testid="admin-menu-toggle"
          @click="toggleMenu"
        >
          <svg v-if="mobileOpen" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            <path d="m6 6 12 12M18 6 6 18" />
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
            <path d="M4 7h16M4 12h16M4 17h16" />
          </svg>
        </button>
      </div>
    </header>

    <aside ref="desktopSidebar" class="admin-sidebar" aria-label="后台导航">
      <div class="admin-sidebar-brand">
        <NuxtLink to="/admin/articles" aria-label="Gavin Studio 后台首页">
          <span>
            <strong>Gavin Studio</strong>
            <small>写作台</small>
          </span>
        </NuxtLink>
      </div>
      <AdminCoreNavigation :path="route.path" />
      <div class="admin-sidebar-tools">
        <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
        <AdminThemeToggle :compact="false" />
        <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
          {{ loggingOut ? '退出中…' : '退出' }}
        </button>
      </div>
    </aside>

    <div
      v-if="mobileOpen"
      class="admin-drawer-backdrop"
      data-testid="admin-drawer-backdrop"
      @click.self="closeMenu(true)"
    >
      <aside
        id="admin-mobile-drawer"
        ref="mobileDrawer"
        class="admin-mobile-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="admin-mobile-drawer-title"
      >
        <div class="admin-drawer-heading">
          <p id="admin-mobile-drawer-title">工作台导航</p>
          <button class="admin-icon-button" type="button" aria-label="关闭导航菜单" @click="closeMenu(true)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
              <path d="m6 6 12 12M18 6 6 18" />
            </svg>
          </button>
        </div>
        <AdminCoreNavigation :path="route.path" />
        <div class="admin-drawer-tools">
          <NuxtLink class="admin-utility-link" to="/"><StudioIcon name="external-link" />查看站点</NuxtLink>
          <AdminThemeToggle :compact="false" />
          <button class="admin-utility-link admin-logout" type="button" :disabled="loggingOut" @click="logout">
            {{ loggingOut ? '退出中…' : '退出' }}
          </button>
        </div>
      </aside>
    </div>

    <main id="admin-main" ref="adminMain" class="admin-main" tabindex="-1">
      <p
        v-if="logoutError"
        class="admin-form-error mb-6"
        role="alert"
        data-testid="logout-error"
      >
        {{ logoutError }}
      </p>
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const mobileOpen = ref(false)
const menuButton = ref<HTMLButtonElement | null>(null)
const mobileDrawer = ref<HTMLElement | null>(null)
const mobileHeader = ref<HTMLElement | null>(null)
const desktopSidebar = ref<HTMLElement | null>(null)
const adminMain = ref<HTMLElement | null>(null)
const loggingOut = ref(false)
const logoutError = ref('')

const setBodyScrollLocked = (locked: boolean) => {
  if (import.meta.client) document.body.style.overflow = locked ? 'hidden' : ''
}

const setBackgroundInert = (locked: boolean) => {
  for (const element of [mobileHeader.value, desktopSidebar.value, adminMain.value]) {
    if (element) element.inert = locked
  }
}

const closeMenu = (returnFocus = false) => {
  mobileOpen.value = false
  setBodyScrollLocked(false)
  setBackgroundInert(false)
  if (returnFocus) nextTick(() => menuButton.value?.focus())
}

const toggleMenu = () => {
  if (mobileOpen.value) {
    closeMenu(true)
  }
  else {
    mobileOpen.value = true
    setBodyScrollLocked(true)
    setBackgroundInert(true)
    nextTick(() => requestAnimationFrame(() => focusableElements()[0]?.focus()))
  }
}

const focusableElements = () => Array.from(
  mobileDrawer.value?.querySelectorAll<HTMLElement>(
    'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])',
  ) ?? [],
).filter(element => !element.hidden)

const onKeydown = (event: KeyboardEvent) => {
  if (!mobileOpen.value) return
  if (event.key === 'Escape') {
    closeMenu(true)
    return
  }
  if (event.key !== 'Tab') return
  const focusable = focusableElements()
  if (!focusable.length) return
  const first = focusable[0]!
  const last = focusable[focusable.length - 1]!
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  }
  else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

const onResize = () => {
  if (window.matchMedia('(min-width: 761px)').matches && mobileOpen.value) closeMenu()
}

watch(() => route.fullPath, () => closeMenu())
onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  window.removeEventListener('resize', onResize)
  setBodyScrollLocked(false)
  setBackgroundInert(false)
})

const logout = async () => {
  if (loggingOut.value) return
  loggingOut.value = true
  logoutError.value = ''
  try {
    await apiFetch('/auth/logout', { method: 'POST' })
    await navigateTo('/admin/login')
  }
  catch (error: unknown) {
    if (apiErrorStatus(error) === 401) {
      await navigateTo('/admin/login')
      return
    }
    logoutError.value = logoutFailureMessage(error)
    if (mobileOpen.value) closeMenu(true)
  }
  finally {
    loggingOut.value = false
  }
}

useSeoMeta({ robots: 'noindex,nofollow' })
</script>
