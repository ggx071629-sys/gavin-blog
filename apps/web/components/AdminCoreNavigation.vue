<template>
  <nav class="admin-core-nav" aria-label="主导航">
    <section v-for="group in ADMIN_NAV_GROUPS" :key="group.label" class="admin-nav-group">
      <h2>{{ group.label }}</h2>
      <NuxtLink
        v-for="item in group.items"
        :key="item.href"
        :to="item.href"
        class="admin-nav-link"
        :class="{ 'admin-nav-link-active': isAdminNavItemActive(path, item.href) }"
        :aria-current="isAdminNavItemActive(path, item.href) ? 'page' : undefined"
      >
        <StudioIcon :name="iconFor(item.href)" />
        <span>{{ item.label }}</span>
      </NuxtLink>
    </section>
  </nav>
</template>

<script setup lang="ts">
import { ADMIN_NAV_GROUPS, isAdminNavItemActive } from '~/utils/admin'

defineProps<{ path: string }>()

const icons = {
  '/admin/articles': 'file-description',
  '/admin/books': 'book',
  '/admin/projects': 'folder',
  '/admin/profile': 'user-square',
  '/admin/account': 'user-square',
  '/admin/about': 'info-circle',
  '/admin/taxonomy': 'tag',
  '/admin/media': 'photo',
  '/admin/content': 'trash',
  '/admin/assistant': 'message-circle',
} as const
const iconFor = (path: string) => icons[path as keyof typeof icons] ?? 'file-description'
</script>
