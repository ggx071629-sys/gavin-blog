<template>
  <header class="site-header sticky top-0 z-40 border-b backdrop-blur-xl">
    <div ref="headerBar" class="page-shell site-header-bar flex items-center justify-between gap-5">
      <NuxtLink to="/" class="site-brand flex min-w-0 items-center gap-2.5" aria-label="Gavin 首页">
        <img class="site-brand-mark" src="/brand/gavin-bird.svg" width="44" height="44" alt="" aria-hidden="true">
        <span class="site-brand-wordmark"><span class="site-brand-name">GAVIN<span aria-hidden="true">.</span></span><span class="site-brand-caption">NOTES ON BUILDING</span></span>
      </NuxtLink>

      <div class="site-desktop-navigation hidden items-center gap-3 xl:flex">
        <nav aria-label="主导航" class="site-primary-navigation flex items-center gap-2">
          <NuxtLink
            v-for="item in navigation"
            :key="item.to"
            class="site-nav-action nav-link"
            :class="{ 'nav-link-active': isActive(item.to) }"
            :to="item.to"
            :aria-current="isActive(item.to) ? 'page' : undefined"
          >
            <SiteNavIcon :name="item.icon" />
            <span>{{ item.label }}</span>
          </NuxtLink>
        </nav>
        <NuxtLink to="/search" class="site-search-action" :aria-current="route.path === '/search' ? 'page' : undefined">
          <svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="11" cy="11" r="7" />
            <path d="m20 20-3.5-3.5" stroke-linecap="round" />
          </svg>
          <span>搜索</span>
        </NuxtLink>
        <ThemeToggle />
        <NuxtLink to="/admin/articles" class="site-nav-action writing-desk-link">写作台</NuxtLink>
      </div>

      <AssistantLauncher />

      <div class="site-mobile-tools flex items-center gap-2 xl:hidden">
        <NuxtLink to="/search" class="site-mobile-search icon-button border-transparent bg-transparent" aria-label="搜索" :aria-current="route.path === '/search' ? 'page' : undefined">
          <svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="11" cy="11" r="7" />
            <path d="m20 20-3.5-3.5" stroke-linecap="round" />
          </svg>
        </NuxtLink>
        <ThemeToggle />
        <button
          ref="mobileMenuButton"
          class="menu-button bg-transparent"
          type="button"
          aria-controls="mobile-navigation"
          :aria-expanded="mobileMenuOpen"
          :aria-label="mobileMenuOpen ? '关闭主导航菜单' : '打开主导航菜单'"
          @click="toggleMenu"
        >
          <span aria-hidden="true" class="grid gap-1.5">
            <span class="h-px w-5 bg-current" />
            <span class="h-px w-5 bg-current" />
            <span class="h-px w-5 bg-current" />
          </span>
          <span class="hidden sm:inline">菜单</span>
        </button>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="mobileMenuOpen && overlay.owner.value === 'nav'"
        class="site-menu-backdrop"
        data-testid="site-menu-backdrop"
        @click.self="closeMenuAndRestoreFocus"
      >
        <div
          id="mobile-navigation"
          ref="mobileDrawer"
          class="site-menu-overlay"
          data-testid="site-menu-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="mobile-navigation-title"
          @click.self="closeMenuAndRestoreFocus"
        >
          <div class="site-menu-overlay-header">
            <p class="site-menu-brand" aria-hidden="true">G / NOTES</p>
            <p id="mobile-navigation-title" class="ee-heading site-menu-overlay-title">主导航</p>
            <button class="icon-button site-menu-close border-transparent bg-transparent" type="button" aria-label="关闭主导航菜单" @click="closeMenuAndRestoreFocus">
              <svg class="site-menu-close-icon size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
                <path d="m6 6 12 12M18 6 6 18" />
              </svg>
              <span class="site-menu-close-label" aria-hidden="true">关闭</span>
            </button>
          </div>
          <nav
            aria-label="移动端主导航"
            class="site-menu-primary-navigation site-menu-nav"
            data-testid="site-menu-primary-navigation"
          >
            <NuxtLink
              v-for="item in mobileNavigation"
              :key="item.to"
              class="site-nav-action site-menu-route nav-link justify-start"
              :class="{ 'nav-link-active': isActive(item.to) }"
              :to="item.to"
              :data-menu-route="item.to"
              :aria-current="isActive(item.to) ? 'page' : undefined"
              @click="closeMenuOnCurrentRoute(item.to)"
            >
              <SiteNavIcon :name="item.icon" />
              <span class="site-menu-route-label">{{ item.label }}</span>
              <span class="site-menu-route-arrow" aria-hidden="true">↗</span>
            </NuxtLink>
          </nav>
          <div class="site-menu-secondary-actions" data-testid="site-menu-secondary-actions">
            <NuxtLink
              to="/admin/articles"
              class="site-nav-action site-menu-writing-desk writing-desk-link justify-start"
              data-testid="site-menu-writing-desk"
              @click="closeMenuOnCurrentRoute('/admin/articles')"
            >
              写作台
            </NuxtLink>
          </div>
        </div>
      </div>
    </Teleport>
  </header>
</template>

<script setup lang="ts">
const route = useRoute()
const overlay = usePublicOverlay()
const mobileMenuOpen = ref(false)
const mobileMenuButton = ref<HTMLButtonElement | null>(null)
const mobileDrawer = ref<HTMLElement | null>(null)
const headerBar = ref<HTMLElement | null>(null)
const navigation = [
  { icon: 'articles', label: '文章', to: '/articles' },
  { icon: 'projects', label: '项目', to: '/projects' },
  { icon: 'books', label: '读书', to: '/books' },
  { icon: 'archive', label: '归档', to: '/archive' },
  { icon: 'about', label: '关于', to: '/about' },
] as const
const mobileNavigation = [
  ...navigation,
  { icon: 'search', label: '搜索', to: '/search' },
] as const

const isActive = (path: string) =>
  route.path === path
  || route.path.startsWith(`${path}/`)
  || (path === '/articles' && route.path.startsWith('/notes/'))

const backgroundElements = () => [
  headerBar.value,
  document.querySelector<HTMLElement>('.skip-link'),
  document.querySelector<HTMLElement>('.assistant-orb-layer'),
  document.querySelector<HTMLElement>('#main-content'),
  document.querySelector<HTMLElement>('footer'),
].filter((element): element is HTMLElement => Boolean(element))

const setBackgroundInert = (locked: boolean) => {
  for (const element of backgroundElements()) {
    element.inert = locked
  }
}

const setBodyScrollLocked = (locked: boolean) => {
  if (import.meta.client) document.body.style.overflow = locked ? 'hidden' : ''
}

const closeMenu = () => {
  if (!mobileMenuOpen.value) return
  mobileMenuOpen.value = false
  setBodyScrollLocked(false)
  setBackgroundInert(false)
  overlay.release('nav', { restoreFocus: false })
}

const closeMenuOnCurrentRoute = (path: string) => {
  if (route.path === path && !route.hash && !Object.keys(route.query).length) closeMenuAndRestoreFocus()
}

const closeMenuAndRestoreFocus = async () => {
  if (!mobileMenuOpen.value) return
  closeMenu()
  await nextTick()
  mobileMenuButton.value?.focus()
}

const focusableElements = () => Array.from(
  mobileDrawer.value?.querySelectorAll<HTMLElement>(
    'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])',
  ) ?? [],
).filter(element => !element.hidden)

const openMenu = () => {
  overlay.claim('nav', { restoreFocus: false })
  mobileMenuOpen.value = true
  setBodyScrollLocked(true)
  nextTick(() => {
    setBackgroundInert(true)
    requestAnimationFrame(() => focusableElements()[0]?.focus())
  })
}

const toggleMenu = () => {
  if (mobileMenuOpen.value) closeMenuAndRestoreFocus()
  else openMenu()
}

const onKeydown = (event: KeyboardEvent) => {
  if (!mobileMenuOpen.value) return
  if (event.key === 'Escape') {
    event.preventDefault()
    closeMenuAndRestoreFocus()
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
  if (window.matchMedia('(min-width: 1280px)').matches && mobileMenuOpen.value) {
    closeMenu()
  }
}

watch(() => route.fullPath, async () => {
  const navigatedFromMenu = mobileMenuOpen.value
  closeMenu()
  if (navigatedFromMenu) {
    await nextTick()
    const target = document.querySelector<HTMLElement>('#main-content, main, h1')
    if (target) {
      if (!target.hasAttribute('tabindex')) target.setAttribute('tabindex', '-1')
      target.focus()
    }
  }
})
watch(() => overlay.owner.value, (owner) => {
  if (owner !== 'nav' && mobileMenuOpen.value) closeMenu()
})
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
</script>

<style scoped>
.site-desktop-navigation {margin-left:auto;}
/* Give the persistent assistant its own row only when the header is too narrow. */
@media(max-width:479px) {
  .site-header-bar:has(.assistant-launcher) {flex-wrap:wrap;padding-block:10px;row-gap:8px;}
  .site-header-bar :deep(.assistant-launcher) {order:3;width:100%;}
}
</style>
