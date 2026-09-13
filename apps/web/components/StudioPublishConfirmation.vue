<template>
  <AdminDialog :model-value="open" :labelledby="titleId" @update:model-value="settle(false)">
    <h2 :id="titleId" class="admin-panel-title">{{ updating ? '更新发布？' : '发布内容？' }}</h2>
    <p class="mt-4 admin-secondary-text">{{ updating ? '已保存的工作副本将替换访客看到的版本。' : '已保存的草稿将对访客公开。' }}取消会保留草稿。</p>
    <div class="mt-6 flex flex-wrap justify-end gap-3">
      <button type="button" class="button-secondary" @click="settle(false)">取消</button>
      <button type="button" class="button-primary" data-testid="confirm-publish" @click="settle(true)">确认发布</button>
    </div>
  </AdminDialog>
</template>
<script setup lang="ts">
const open = ref(false)
const updating = ref(false)
const titleId = useId()
let resolveDecision: ((accepted: boolean) => void) | null = null
const settle = (accepted: boolean) => {
  open.value = false
  const resolve = resolveDecision
  resolveDecision = null
  resolve?.(accepted)
}
const request = (published: boolean): Promise<boolean> => {
  if (resolveDecision) return Promise.resolve(false)
  updating.value = published
  open.value = true
  return new Promise(resolve => { resolveDecision = resolve })
}
onBeforeUnmount(() => settle(false))
defineExpose({ request })
</script>
