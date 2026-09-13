<template>
  <section class="resource-ops studio-media">
    <header class="admin-page-header"><div>
      <h1 class="mt-3 text-3xl font-semibold">媒体库</h1>
      <p class="mt-3 text-sm text-ee-ink-faint">先选择已有图片，或在下方上传与登记外链。复制后可回到编辑器粘贴；移除媒体保留历史引用。</p>
    </div><a href="#media-add" class="button-primary">添加图片</a></header>
    <div class="mt-8">
      <MediaUploader management show-library-default @insert="copyMarkdown" @selected="copyUrl" />
    </div>
    <div v-if="copied || copyError" class="mt-4" aria-live="polite">
      <p :class="copyError ? 'text-ee-danger-ink' : 'text-ee-success-ink'">{{ copyError || copied }}</p>
      <label v-if="copyError" class="field mt-3"><span>可手动选择并复制</span><textarea :value="copyValue" readonly rows="3" @focus="($event.target as HTMLTextAreaElement).select()" /></label>
      <NuxtLink class="admin-inline-action mt-2" to="/admin/articles">返回文章管理</NuxtLink>
    </div>
  </section>
</template>

<script setup lang="ts">
import '~/assets/css/resource-operations.css'
definePageMeta({ layout: 'admin-core', middleware: 'admin' })
const copied = ref('')
const copyError = ref('')
const copyValue = ref('')
const copy = async (value: string, label: string) => {
  copied.value = ''
  copyError.value = ''
  copyValue.value = value
  try {
    await navigator.clipboard.writeText(value)
    copied.value = label
  }
  catch { copyError.value = '剪贴板不可用，请手动复制下方内容。' }
}
const copyMarkdown = (value: string) => copy(value, 'Markdown 已复制。')
const copyUrl = (value: string) => copy(value, 'URL 已复制。')
useSeoMeta({ title: '媒体库' })
</script>

<style scoped>
.studio-media { max-width: none; margin: 0; --ee-ink-faint: var(--studio-muted); }
.studio-media h1 { font-size: 36px; margin: 0; }
@media (max-width: 760px) { .studio-media h1 { font-size: 28px; } }
</style>
