<template>
  <article data-focus-card class="project-ledger-row blueprint-card p-6 rounded-xl relative overflow-hidden flex flex-col justify-between group transition-all" data-testid="project-card">
    <BlueprintWatermark :value="displayIndex" />
    <NuxtLink :to="project.public_path" class="project-ledger-link flex flex-col justify-between h-full space-y-4 relative z-10">
      <div class="space-y-2">
        <div class="flex items-center justify-between font-mono text-sm">
          <span class="ee-label project-ledger-index text-[var(--ee-primary)] font-bold">[SYS-{{ displayIndex }}]</span>
          <span v-if="project.related_articles.length" class="ee-label project-ledger-meta text-[var(--ee-ink-faint)]">
            {{ project.related_articles.length }} 篇笔记
          </span>
        </div>
        <span class="project-ledger-copy block space-y-2">
          <span class="ee-heading project-ledger-title text-xl font-bold text-[var(--ee-ink)] group-hover:text-[var(--ee-primary)] transition-colors block">
            {{ project.title }}
          </span>
          <span v-if="project.summary" class="project-ledger-summary text-sm text-[var(--ee-ink-muted)] leading-relaxed block line-clamp-3">
            {{ project.summary }}
          </span>
        </span>
      </div>
      <div class="pt-3 border-t border-[var(--ee-line)] flex items-center justify-between font-mono text-sm text-[var(--ee-ink-faint)]">
        <span>工程交付详情</span>
        <NavigationArrow />
      </div>
    </NuxtLink>
  </article>
</template>

<script setup lang="ts">
import type { PublicProject } from '~/types/api'

const props = withDefaults(defineProps<{
  project: PublicProject
  index?: number
}>(), { index: 0 })

const displayIndex = computed(() => String(props.index + 1).padStart(2, '0'))
</script>
