<template>
  <div class="site-section-heading" :class="{ 'site-section-intro': variant === 'intro' }">
    <component :is="tag" :id="titleId" class="site-section-name">{{ label }}</component>
    <span class="site-section-rule" aria-hidden="true" />
    <slot />
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  label: string
  tag?: 'span' | 'h2'
  titleId?: string
  variant?: 'intro' | 'section'
}>(), { tag: 'span', variant: 'intro', titleId: undefined })
</script>

<style scoped>

.site-section-heading {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 28px;
}
.site-section-name {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
  margin: 0;
  color: var(--ee-ink);
  font: 700 26px/1.4 var(--ee-heading);
  letter-spacing: -.02em;
}
.site-section-name::before {
  content: '';
  width: 9px;
  height: 9px;
  flex-shrink: 0;
  border-radius: 2px;
  transform: rotate(45deg);
  background: var(--ee-primary);
}
.site-section-intro .site-section-name {
  font-size: 18px;
  color: var(--ee-primary-strong);
  letter-spacing: .06em;
}
.site-section-rule { flex: 1; min-width: 12px; height: 1px; background: var(--ee-line); }
:slotted(.site-section-link) { display: inline-flex; align-items: center; gap: 8px; min-height: 44px; color: var(--ee-ink-muted); font-size: 14px; font-weight: 600; white-space: nowrap; }
:slotted(.site-section-link):hover { color: var(--ee-primary-strong); }
@media (max-width: 639px) {
  .site-section-heading { gap: 12px; margin-bottom: 24px; }
  .site-section-name { font-size: 22px; gap: 8px; }
  .site-section-name::before { width: 8px; height: 8px; }
  .site-section-intro .site-section-name { font-size: 16px; }
}
</style>
