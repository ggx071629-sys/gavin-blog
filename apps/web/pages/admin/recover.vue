<template>
  <main class="admin-login-shell">
    <div class="admin-login-theme"><AdminThemeToggle /></div>
    <section class="admin-login-form-stage">
      <div class="admin-login-card">
        <p class="studio-login-label">GAVIN STUDIO / 私人工作区</p>
        <h1 class="admin-page-title">找回密码</h1>
        <p class="admin-page-description">验证码仅发送到服务器配置的固定安全邮箱。请在邮箱中查看，不需要输入邮箱或登录名。</p>
        <div class="admin-login-form"><AccountPasswordForm recovery /></div>
        <NuxtLink to="/admin/login" class="admin-login-back">返回登录</NuxtLink>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
definePageMeta({ layout: false })
useSeoMeta({ title: '找回密码', robots: 'noindex,nofollow' })
</script>
