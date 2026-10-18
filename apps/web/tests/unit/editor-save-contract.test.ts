import { readFileSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const webRoot = resolve(process.cwd())
const editorFiles = [
  'components/ArticleEditor.vue',
  'components/ProjectEditor.vue',
  'components/BookNoteEditor.vue',
]

describe('editor save safety contract', () => {
  it.each(editorFiles)('%s uses the shared navigation and unload barrier', (relativePath) => {
    const source = readFileSync(join(webRoot, relativePath), 'utf8')

    expect(source).toContain('useAutosaveSafety(')
    expect(source).not.toMatch(/on(?:Before)?Unmounted\(\(\) => queue\?*\.dispose\(\)\)/)
  })

  it('disables published slugs and sends article publish versions', () => {
    const article = readFileSync(join(webRoot, 'components/ArticleEditor.vue'), 'utf8')
    const project = readFileSync(join(webRoot, 'components/ProjectEditor.vue'), 'utf8')
    const book = readFileSync(join(webRoot, 'components/BookNoteEditor.vue'), 'utf8')
    expect(article).toContain(':disabled="current.status === \'published\'"')
    expect(project).toContain(':disabled="current.status === \'published\'"')
    expect(book).toContain(':disabled="current.status === \'published\'"')
    expect(article).toContain('body: { version: current.value.version }')
    expect(article).toContain('useApiFailure(')
    expect(article).toContain('isCompleteReference')
    expect(article).toContain('publishError.value')
  })

  it('surfaces trash errors and published preview honestly', () => {
    const trash = readFileSync(join(webRoot, 'pages/admin/content.vue'), 'utf8')
    const preview = readFileSync(join(webRoot, 'pages/admin/articles/[id]/preview.vue'), 'utf8')
    const articles = readFileSync(join(webRoot, 'pages/articles/index.vue'), 'utf8')
    const project = readFileSync(join(webRoot, 'pages/projects/[slug].vue'), 'utf8')
    expect(trash).toContain('trashError')
    expect(preview).toContain("article.status === 'published'")
    expect(preview).toContain('工作副本预览')
    expect(articles).toContain('total_article_count')
    expect(project).toContain('absoluteSiteUrl(config.public.siteUrl, project.value.public_path)')
  })
})
