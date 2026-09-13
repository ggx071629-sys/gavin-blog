<template>
  <StudioContentList kind="books" heading="读书笔记" description="记录读过的书，以及值得留下的想法。" create-label="新建读书笔记" />
</template>
<script setup lang="ts">
definePageMeta({ layout: 'admin-core', middleware: 'admin' })
useSeoMeta({ title: '读书笔记管理' })
</script>
