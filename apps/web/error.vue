<template>
  <section class="error-stage public-error blueprint-wrapper">
    <div class="page-shell relative z-10 flex min-h-[calc(100vh-11rem)] items-center py-16">
      <div data-focus-card class="error-content blueprint-card p-8 sm:p-12 rounded-2xl relative overflow-hidden space-y-6">
        <SectionHeading :label="`页面状态 ${statusCode}`" class="relative z-10" />

        <div class="relative z-10 space-y-4">
          <h1 class="ee-heading text-3xl sm:text-5xl font-black tracking-tight text-[var(--ee-ink)]">{{ errorTitle }}</h1>
          <div class="about-quote-box p-4 rounded-lg">
            <p class="text-base sm:text-lg text-[var(--ee-ink-muted)] leading-relaxed">
              {{ errorMessage }}
            </p>
          </div>
        </div>

        <nav class="error-actions relative z-10" aria-label="错误恢复">
          <button type="button" data-focus-card class="error-action" @click="retry">
            <span>重试当前页面</span><span aria-hidden="true">↻</span>
          </button>
          <NuxtLink to="/" data-focus-card class="error-action" @click.prevent="leaveTo('/')">
            <span>返回首页</span><span aria-hidden="true">&rarr;</span>
          </NuxtLink>
          <NuxtLink to="/search" data-focus-card class="error-action" @click.prevent="leaveTo('/search')">
            <span>搜索博客</span><span aria-hidden="true">⌕</span>
          </NuxtLink>
          <NuxtLink to="/articles" data-focus-card class="error-action" @click.prevent="leaveTo('/articles')">
            <span>浏览文章</span><span aria-hidden="true">▤</span>
          </NuxtLink>
        </nav>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import SectionHeading from '~/components/SectionHeading.vue'
import type { NuxtError } from '#app'

usePublicCardFocus()

const props = defineProps<{ error: NuxtError }>()
const statusCode = computed(() => props.error.statusCode || 500)
const errorTitle = computed(() => ({
  401: '需要登录',
  403: '请求未通过安全校验',
  404: '页面不存在',
  429: '请求过于频繁',
  503: '服务暂时不可用',
}[statusCode.value] || '系统暂时不可用'))
const errorMessage = computed(() => {
  if (statusCode.value === 404) return '你访问的路径可能已经移动、删除，或者从未存在。'
  if (statusCode.value === 401) return '当前操作需要有效的管理会话，请重新登录后继续。'
  if (statusCode.value === 403) return '请求没有通过权限或安全校验。请刷新页面后重试。'
  if (statusCode.value === 429) return '请求频率超过限制，请稍后再试。'
  return '上游服务没有成功完成请求。请稍后重试；你可以重试当前页面，或稍后回来。'
})
const retry = () => reloadNuxtApp({ force: true })
// 错误页会一直渲染到错误状态被清除；仅靠路由跳转不会重新挂载目标页面。
const leaveTo = (path: string) => clearError({ redirect: path })

useHead({ title: () => `${statusCode.value} · ${errorTitle.value}` })
</script>
