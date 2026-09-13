<template>
  <Teleport to="body">
    <div
      v-if="modelValue"
      class="admin-modal-backdrop"
      :data-testid="testId"
      @mousedown.self="requestClose"
    >
      <section
        ref="dialog"
        class="admin-modal"
        :class="widthClass"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="labelledby"
        :aria-describedby="describedby"
        tabindex="-1"
        @keydown="onKeydown"
      >
        <slot />
      </section>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  modelValue: boolean
  labelledby: string
  describedby?: string
  testId?: string
  widthClass?: string
  closeDisabled?: boolean
}>(), {
  describedby: undefined,
  testId: undefined,
  widthClass: '',
  closeDisabled: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const dialog = ref<HTMLElement | null>(null)
let returnTarget: HTMLElement | null = null

const focusableSelector = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

const focusables = () =>
  Array.from(dialog.value?.querySelectorAll<HTMLElement>(focusableSelector) ?? [])
    .filter(element => !element.hidden && element.getAttribute('aria-hidden') !== 'true')

const requestClose = () => {
  if (!props.closeDisabled) emit('update:modelValue', false)
}

const onKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Escape') {
    event.preventDefault()
    requestClose()
    return
  }
  if (event.key !== 'Tab') return

  const items = focusables()
  if (!items.length) {
    event.preventDefault()
    dialog.value?.focus()
    return
  }

  const first = items[0]
  const last = items[items.length - 1]
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last?.focus()
  }
  else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first?.focus()
  }
}

watch(() => props.modelValue, async (open) => {
  if (!import.meta.client) return
  if (open) {
    returnTarget = document.activeElement instanceof HTMLElement ? document.activeElement : null
    document.body.style.overflow = 'hidden'
    await nextTick()
    const preferred = dialog.value?.querySelector<HTMLElement>('[autofocus]')
    const target = preferred ?? focusables()[0] ?? dialog.value
    target?.focus()
  }
  else {
    document.body.style.overflow = ''
    await nextTick()
    returnTarget?.focus()
    returnTarget = null
  }
})

onBeforeUnmount(() => {
  if (!import.meta.client) return
  document.body.style.overflow = ''
  returnTarget?.focus()
})
</script>
