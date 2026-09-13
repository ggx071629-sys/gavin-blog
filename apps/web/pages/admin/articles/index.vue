<template>
  <StudioContentList kind="articles" heading="文章" description="从草稿到发布，让每一篇内容都有清晰的进度。" create-label="新建草稿" />
</template>
<script setup lang="ts">
definePageMeta({ layout: 'admin-core', middleware: 'admin' })
useSeoMeta({ title: '文章管理' })
</script>
