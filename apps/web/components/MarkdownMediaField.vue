<template>
  <section class="field" :class="{ 'studio-markdown-field': studioTools }">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <label :for="textareaId">Markdown</label>
      <div class="flex flex-wrap items-center gap-2">
        <label class="button-secondary cursor-pointer">
          从设备插入图片
          <input class="sr-only" type="file" accept="image/jpeg,image/png,image/webp,image/avif" multiple @change="selectFiles">
        </label>
        <MediaUploader library-only @insert="insertExisting" />
      </div>
    </div>
    <div v-if="studioTools" class="studio-markdown-tools" role="group" aria-label="Markdown 工具栏">
      <button type="button" @click="formatSelection('heading')">标题</button>
      <button type="button" @click="formatSelection('bold')">加粗</button>
      <button type="button" @click="formatSelection('quote')">引用</button>
      <button type="button" @click="formatSelection('link')">链接</button>
    </div>
    <textarea
      :id="textareaId"
      ref="textarea"
      :value="modelValue"
      :data-testid="testId"
      :class="minHeightClass"
      class="mt-2 font-mono text-sm leading-6"
      spellcheck="false"
      @input="onInput"
      @click="rememberSelection"
      @keyup="rememberSelection"
      @select="rememberSelection"
      @paste="pasteFiles"
      @dragover.prevent
      @drop.prevent="dropFiles"
    />
    <p v-if="studioTools" class="studio-word-count">Markdown · {{ Array.from(modelValue.replace(/\s/g, '')).length }} 个非空白字符</p>
    <p class="mt-2 text-sm text-ee-ink-muted">
      可直接粘贴或拖入图片。上传会先在当前光标处放置占位；发布前必须补齐图片 Alt。
    </p>
    <ul v-if="tasks.length" class="mt-3 space-y-2 text-sm" aria-live="polite">
      <li v-for="task in tasks" :key="task.id" class="flex flex-wrap items-center justify-between gap-2 rounded-ee-soft bg-ee-surface-low px-3 py-2">
        <span class="truncate">{{ task.file.name }} · {{ task.status === 'uploading' ? '上传中…' : '上传失败' }}</span>
        <span v-if="task.status === 'error'" class="flex gap-2">
          <button class="admin-inline-action" type="button" @click="retry(task)">重试</button>
          <button class="admin-inline-action text-ee-danger-ink" type="button" @click="remove(task)">移除占位</button>
        </span>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import type { MediaAsset } from '~/types/api'
import { resolvePublicUrl } from '~/utils/api-url'
import { insertAtRange, replaceMediaMarker } from '~/utils/markdown-media'

interface UploadTask {
  id: string
  file: File
  marker: string
  status: 'uploading' | 'error'
}

const props = withDefaults(defineProps<{
  modelValue: string
  testId?: string
  minHeightClass?: string
}>(), {
  testId: undefined,
  minHeightClass: 'min-h-[28rem]',
})

const studioTools = inject('studio-writing-tools', false)
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const textareaId = useId()
const textarea = ref<HTMLTextAreaElement | null>(null)
const tasks = ref<UploadTask[]>([])
const selection = reactive({ start: props.modelValue.length, end: props.modelValue.length })

const setValue = (value: string) => emit('update:modelValue', value)
const rememberSelection = () => {
  if (!textarea.value) return
  selection.start = textarea.value.selectionStart
  selection.end = textarea.value.selectionEnd
}
const focusAt = async (position: number) => {
  await nextTick()
  textarea.value?.focus()
  textarea.value?.setSelectionRange(position, position)
  selection.start = selection.end = position
}
const insertText = (text: string) => {
  const next = insertAtRange(props.modelValue, text, selection.start, selection.end)
  const position = selection.start + text.length
  setValue(next)
  void focusAt(position)
}
const formatSelection = (kind: 'heading' | 'bold' | 'quote' | 'link') => {
  rememberSelection()
  const selected = props.modelValue.slice(selection.start, selection.end)
  const text = kind === 'heading' ? `## ${selected || '标题'}`
    : kind === 'bold' ? `**${selected || '加粗文字'}**`
    : kind === 'quote' ? `> ${(selected || '引用文字').replace(/\n/g, '\n> ')}`
    : `[${selected || '链接文字'}](https://)`
  insertText(text)
}
const onInput = (event: Event) => {
  setValue((event.target as HTMLTextAreaElement).value)
  rememberSelection()
}

const upload = async (task: UploadTask) => {
  task.status = 'uploading'
  try {
    const body = new FormData()
    body.append('file', task.file)
    body.append('alt_text', '')
    const asset = await apiFetch<MediaAsset>('/admin/media', { method: 'POST', body })
    const markdown = `\n\n![](${resolvePublicUrl(asset.url)})\n`
    setValue(replaceMediaMarker(props.modelValue, task.marker, markdown))
    tasks.value = tasks.value.filter(item => item.id !== task.id)
  }
  catch {
    const failedMarker = `\n\n<!-- media:${task.id}:failed -->\n`
    setValue(replaceMediaMarker(props.modelValue, task.marker, failedMarker))
    task.marker = failedMarker
    task.status = 'error'
  }
}

const importFiles = async (files: File[]) => {
  const images = files.filter(file => file.type.startsWith('image/'))
  for (const file of images) {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`
    const marker = `\n\n<!-- media:${id}:uploading -->\n`
    const task: UploadTask = { id, file, marker, status: 'uploading' }
    tasks.value.push(task)
    insertText(marker)
    await nextTick()
    await upload(task)
  }
}
const selectFiles = async (event: Event) => {
  rememberSelection()
  const input = event.target as HTMLInputElement
  await importFiles(Array.from(input.files ?? []))
  input.value = ''
}
const pasteFiles = (event: ClipboardEvent) => {
  const files = Array.from(event.clipboardData?.items ?? [])
    .filter(item => item.kind === 'file')
    .map(item => item.getAsFile())
    .filter((file): file is File => file !== null)
  if (!files.length) return
  event.preventDefault()
  rememberSelection()
  void importFiles(files)
}
const dropFiles = (event: DragEvent) => {
  rememberSelection()
  void importFiles(Array.from(event.dataTransfer?.files ?? []))
}
const retry = async (task: UploadTask) => {
  const uploadingMarker = `\n\n<!-- media:${task.id}:uploading -->\n`
  setValue(replaceMediaMarker(props.modelValue, task.marker, uploadingMarker))
  task.marker = uploadingMarker
  await nextTick()
  await upload(task)
}
const remove = (task: UploadTask) => {
  setValue(replaceMediaMarker(props.modelValue, task.marker, ''))
  tasks.value = tasks.value.filter(item => item.id !== task.id)
}
const insertExisting = (markdown: string) => {
  rememberSelection()
  insertText(markdown)
}
</script>
