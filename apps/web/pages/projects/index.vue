<template>
  <section class="page-shell public-page projects-index max-w-4xl mx-auto space-y-6">
    <PublicPageHero
      class="projects-intro"
      label="项目实践"
      artwork="projects"
      title="我做过的项目"
      description="这里整理项目的用途、实现方式和开发过程，也收录相关技术笔记。"
    />

    <div
      class="projects-results space-y-10"
      data-testid="projects-results"
      :aria-busy="listBusy ? 'true' : 'false'"
    >
      <section v-if="lead" data-focus-card class="projects-lead blueprint-card p-6 sm:p-8 rounded-2xl relative overflow-hidden space-y-6" data-testid="projects-lead">
        <BlueprintWatermark :value="1" />
        <div class="projects-lead-signal flex flex-wrap items-center gap-3 font-mono text-sm relative z-10">
          <span class="status-chip chip-blue">工程实践</span>
          <p v-if="lead.related_articles.length" class="ee-label text-[var(--ee-ink-faint)]">
            {{ lead.related_articles.length }} 篇工程复盘笔记
          </p>
        </div>
        <div class="projects-lead-identity space-y-3 relative z-10">
          <h2 class="ee-heading projects-lead-title text-2xl sm:text-3xl font-black text-[var(--ee-ink)] leading-snug">
            <NuxtLink :to="lead.public_path" class="hover:text-[var(--ee-primary)] transition-colors">{{ lead.title }}</NuxtLink>
          </h2>
          <p v-if="lead.summary" class="projects-lead-summary text-base text-[var(--ee-ink-muted)] leading-relaxed">{{ lead.summary }}</p>
        </div>
        <div class="projects-lead-actions flex flex-wrap items-center gap-4 pt-2 relative z-10">
          <NuxtLink :to="lead.public_path" class="projects-lead-cta">
            查看架构设计案 <NavigationArrow />
          </NuxtLink>
          <a
            v-if="lead.repository_url"
            :href="lead.repository_url"
            class="projects-lead-source"
            target="_blank"
            rel="noreferrer"
          >查看源码库 <NavigationArrow direction="up-right" /></a>
        </div>
        <div class="ee-accent-electric" aria-hidden="true" />
      </section>

      <div v-if="ledger.length" class="space-y-6">
        <header class="projects-ledger-header"><h2 class="projects-ledger-heading">其他工程交付</h2></header>
        <div class="projects-ledger grid grid-cols-1 md:grid-cols-2 gap-6">
          <ProjectCard
            v-for="(project, index) in ledger"
            :key="project.id"
            :project="project"
            :index="ledgerIndex(index)"
          />
        </div>
      </div>
      <div v-else-if="!lead && !listBusy" data-focus-card class="empty-state">暂时还没有已发布项目。</div>
      <p v-if="listBusy" class="public-loading" role="status">正在读取内容…</p>
      <PaginationNav :page="page" :has-next="hasNext" path="/projects" />
    </div>
  </section>
</template>

<script setup lang="ts">
import type { PublicProject } from '~/types/api'
import { paginatedApiPath, paginationWindow } from '~/utils/pagination'

const pageSize = 12
const page = useBoundedPage(pageSize)
const endpoint = computed(() => paginatedApiPath('/projects', page.value, pageSize))
const { data: projectRows, pending, error } = await useAsyncData(
  'projects',
  (_nuxtApp, { signal }) => apiFetch<PublicProject[]>(endpoint.value, { signal }),
  { watch: [endpoint] },
)
useApiFailure(error)
const window = computed(() => paginationWindow(projectRows.value, pageSize))
const projects = computed(() => window.value.items)
const hasNext = computed(() => window.value.hasNext)
const listBusy = computed(() => Boolean(pending.value))
const lead = computed(() => projects.value[0] || null)
const ledger = computed(() => projects.value.slice(1))
const ledgerIndex = (index: number) => ((page.value - 1) * pageSize) + index + 1

useSiteSeo(() => ({
  title: '项目',
  description: 'Gavin 的项目介绍、实现方式、开发记录与相关技术笔记。',
  jsonLd: {
    '@context': 'https://schema.org',
    '@type': 'CollectionPage',
    name: '项目',
    description: 'Gavin 的项目介绍、实现方式、开发记录与相关技术笔记。',
    inLanguage: 'zh-CN',
  },
}))
</script>
