<template>
  <StudioContentList kind="projects" heading="项目" description="整理做过的项目，记录问题、选择与结果。" create-label="新建项目" />
</template>
<script setup lang="ts">
definePageMeta({ layout: 'admin-core', middleware: 'admin' })
useSeoMeta({ title: '项目管理' })
</script>
