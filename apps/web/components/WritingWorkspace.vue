<template>
  <div ref="root" class="writing-workspace studio-writing-workspace" :data-panel="panel" :data-mode="mode" @input="clearFieldError">
    <div class="writing-mobile-tabs" role="group" aria-label="写作区域">
      <button type="button" :aria-pressed="panel === 'body'" :aria-controls="bodyId" @click="showPanel('body')">正文</button>
      <button type="button" :aria-pressed="panel === 'settings'" :aria-controls="settingsId" @click="showPanel('settings')">设置</button>
    </div>
    <p v-if="error" :id="errorId" role="alert" class="admin-form-error writing-validation">{{ error }}</p>
    <div class="writing-columns">
      <div :id="bodyId" class="writing-body">
        <slot name="title" />
        <div class="writing-mode-bar" role="group" aria-label="正文显示">
          <button type="button" :aria-pressed="mode === 'markdown'" :aria-controls="markdownId" @click="mode = 'markdown'">Markdown</button>
          <button type="button" :aria-pressed="mode === 'preview'" :aria-controls="previewId" @click="mode = 'preview'">预览</button>
          <span>工作副本 · 发布后公开</span>
        </div>
        <div v-show="mode === 'markdown'" :id="markdownId" class="writing-markdown"><slot name="body" /></div>
        <div v-show="mode === 'preview'" :id="previewId" class="writing-preview">
          <template v-if="mode === 'preview'">
            <p class="admin-empty-note">工作副本预览，尚未发布的修改不会出现在公开站点。</p>
            <slot name="preview" />
          </template>
        </div>
      </div>
      <aside :id="settingsId" class="writing-settings" aria-label="内容设置">
        <h2>内容设置</h2>
        <p class="admin-empty-note">路径、摘要与关联信息。已发布路径保持不变。</p>
        <slot name="settings" />
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
provide('studio-writing-tools', true)
const root = ref<HTMLElement | null>(null)
const panel = ref<'body' | 'settings'>('body')
const mode = ref<'markdown' | 'preview'>('markdown')
const error = ref('')
const baseId = useId()
const bodyId = `${baseId}-body`
const settingsId = `${baseId}-settings`
const markdownId = `${baseId}-markdown`
const previewId = `${baseId}-preview`
const errorId = `${baseId}-error`
let invalidField: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement | null = null

const showPanel = async (next: 'body' | 'settings') => {
  panel.value = next
  await nextTick()
  root.value?.querySelector<HTMLElement>(next === 'body' ? '.writing-body' : '.writing-settings')?.scrollIntoView({ block: 'start' })
}
const reveal = async (selector: string) => {
  const target = root.value?.querySelector<HTMLElement>(selector)
  if (!target) return
  panel.value = target.closest('.writing-settings') ? 'settings' : 'body'
  if (target.closest('.writing-markdown')) mode.value = 'markdown'
  await nextTick()
  target.focus()
  target.scrollIntoView({ block: 'center' })
}
const focusInvalid = async () => {
  if (invalidField) await reveal('[data-writing-invalid]')
}
const clearFieldError = (event: Event) => {
  const target = event.target as HTMLElement
  if (!target.hasAttribute('data-writing-invalid')) return
  target.removeAttribute('data-writing-invalid')
  target.removeAttribute('aria-invalid')
  target.removeAttribute('aria-describedby')
  invalidField = null
  error.value = ''
}
const validate = async (focus = true) => {
  root.value?.querySelectorAll('[data-writing-invalid]').forEach(field => {
    field.removeAttribute('data-writing-invalid')
    field.removeAttribute('aria-invalid')
    field.removeAttribute('aria-describedby')
  })
  const fields = root.value?.querySelectorAll<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>('input, textarea, select') ?? []
  invalidField = Array.from(fields).find(field => !field.disabled && (!field.validity.valid || (field.required && !field.value.trim()))) ?? null
  if (!invalidField) { error.value = ''; return true }
  const label = invalidField.closest('label')?.querySelector('span')?.textContent || '字段'
  // 字段可用 data-writing-error 覆盖通用分类文案（例如同时接受站内媒体地址的封面字段）。
  error.value = invalidField.getAttribute('data-writing-error')
    || (invalidField.type === 'url'
    ? `请填写以 http:// 或 https:// 开头的有效${label}。`
    : invalidField.validity.patternMismatch
    ? `${label} 只能使用小写英文字母、数字和单个连字符。`
    : invalidField.validity.typeMismatch ? `请填写有效的${label}。` : `请填写${label}。`)
  invalidField.setAttribute('aria-invalid', 'true')
  invalidField.setAttribute('aria-describedby', errorId)
  invalidField.setAttribute('data-writing-invalid', '')
  if (focus) await focusInvalid()
  return false
}
defineExpose({ validate, reveal, focusInvalid })
</script>
