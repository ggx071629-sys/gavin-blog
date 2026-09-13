import { readFileSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const webRoot = resolve(process.cwd())
const source = (relativePath: string) => readFileSync(join(webRoot, relativePath), 'utf8')

const publicDataPages = [
  'pages/index.vue',
  'pages/articles/index.vue',
  'pages/projects/index.vue',
  'pages/books/index.vue',
  'pages/archive.vue',
  'pages/search.vue',
  'pages/about.vue',
]
const publicDetailPages = [
  'pages/notes/[year]/[month]/[slug].vue',
  'pages/projects/[slug].vue',
  'pages/books/[year]/[month]/[slug].vue',
]
const adminDataSurfaces = [
  'pages/admin/content.vue',
  'pages/admin/taxonomy.vue',
  'pages/admin/articles/[id]/edit.vue',
  'pages/admin/articles/[id]/preview.vue',
  'pages/admin/projects/[id]/edit.vue',
  'pages/admin/books/[id]/edit.vue',
  'pages/admin/profile.vue',
  'pages/admin/articles/new.vue',
  'pages/admin/projects/new.vue',
  'components/ArticleEditor.vue',
]

describe('failure state page contracts', () => {
  it.each(publicDataPages)('%s distinguishes API failure from empty data', (relativePath) => {
    expect(source(relativePath)).toContain('useApiFailure(')
  })

  it.each(publicDetailPages)('%s maps only explicit upstream 404 to not found', (relativePath) => {
    const page = source(relativePath)
    expect(page).toContain('useApiFailure(')
    expect(page).not.toMatch(/error\.value\s*\|\|[^\n]+statusCode:\s*404/)
  })

  it.each(adminDataSurfaces)('%s does not render a load failure as an empty list', (relativePath) => {
    expect(source(relativePath)).toContain('useApiFailure(')
  })

  it('keeps shared Studio lists and media errors separate from empty results', () => {
    for (const kind of ['articles', 'projects', 'books']) {
      expect(source(`pages/admin/${kind}/index.vue`)).toContain(`<StudioContentList kind="${kind}"`)
    }
    const list = source('components/StudioContentList.vue')
    expect(list).toMatch(/v-if="pending"[\s\S]*v-else-if="error"[\s\S]*<template v-else>[\s\S]*v-if="items.length"/)
    expect(list).toContain('@click="refresh()">重新读取</button>')
    const media = source('components/MediaUploader.vue')
    expect(media).toContain('v-if="loadError"')
    expect(media).toContain('@click="refresh()">重新读取媒体</button>')
    expect(media).toContain('v-if="assets?.length && !loadError && libraryStatus !== \'pending\'"')
    expect(media).toContain('v-else-if="!loadError && libraryStatus !== \'pending\'"')
  })

  it('keeps assistant host visibility delegated to the shared entry guard', () => {
    const host = source('components/AssistantHost.vue')
    const entry = source('composables/useAssistantEntry.ts')
    expect(host).toContain('const entry = useAssistantEntry()')
    expect(host).toContain('const visible = entry.visible')
    expect(entry).toContain('available.value && isAssistantUiEnabled(config.public.assistantUiEnabled) && isAssistantLauncherPath(route.path)')
    expect(entry).toContain('if (visible.value)')
  })

  it('keeps session, login, and logout failure semantics distinct', () => {
    expect(source('middleware/admin.ts')).toContain('apiErrorStatus(error) === 401')
    expect(source('pages/admin/login.vue')).toContain('loginFailureMessage(error)')
    expect(source('layouts/admin-core.vue')).toContain('logoutFailureMessage(error)')
    expect(source('layouts/admin-core.vue')).not.toMatch(/finally\s*\{\s*await navigateTo\('\/admin\/login'\)/)
  })
})
