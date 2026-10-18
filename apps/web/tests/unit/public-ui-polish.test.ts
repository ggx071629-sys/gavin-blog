import { readFileSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const webRoot = resolve(process.cwd())
const read = (...segments: string[]) => readFileSync(join(webRoot, ...segments), 'utf8')

describe('public UI polish guardrails', () => {
  it('labels desktop search and keeps the writing desk visually secondary', () => {
    const header = read('components', 'SiteHeader.vue')

    expect(header).toContain('class="site-search-action"')
    expect(header).toContain('<span>搜索</span>')
    expect(header).toContain('class="site-nav-action writing-desk-link"')
    expect(header).not.toContain('class="site-nav-action button-primary">写作台')
    expect(header).toContain("path === '/articles' && route.path.startsWith('/notes/')")
    expect(header).toContain(':aria-current="isActive(item.to) ? \'page\' : undefined"')
  })

  it('hides empty article summaries instead of rendering a placeholder', () => {
    const card = read('components', 'ArticleCard.vue')

    expect(card).toContain('v-if="article.summary.trim()"')
    expect(card).not.toContain('一篇尚未添加摘要的技术笔记。')
  })

  it('keeps about portraits in color and widens the article table of contents', () => {
    const about = read('pages', 'about.vue')
    const css = read('assets', 'css', 'main.css')

    expect(about).not.toMatch(/\bgrayscale\b/)
    expect(css).toContain('lg:grid-cols-[minmax(0,1fr)_18rem]')
    expect(css).toContain('--ee-reading-width: 45rem;')
    expect(css).toContain('grid-template-columns: var(--ee-reading-width) 13.75rem;')
    expect(css).toContain('--article-code-bg:')
    expect(css).toContain('article-signal-rail')
    expect(css).toContain('text-wrap: pretty;')
  })

  it('keeps public article chrome in reader language', () => {
    const page = read('pages', 'notes', '[year]', '[month]', '[slug].vue')

    expect(page).toContain('<ReadingLayout')
    expect(page).not.toContain('article-signal-rail')
    expect(page).toContain('>相关文章<')
    expect(page).not.toContain('Article signal')
    expect(page).not.toMatch(/adaptive/i)
  })

  it('keeps the homepage hero focused without the redundant content-track strip', () => {
    const page = read('pages', 'index.vue')
    const css = read('assets', 'css', 'main.css')

    expect(page).not.toContain('home-tracks')
    expect(page).not.toContain('const tracks')
    expect(css).not.toContain('.home-tracks')
    expect(css).not.toContain('.home-track')
  })

  it('uses one medium outlined index treatment for every homepage article card', () => {
    const card = read('components', 'ArticleCard.vue')
    const css = read('assets', 'css', 'main.css')

    expect(card.match(/class="article-card-index"/g)).toHaveLength(1)
    expect(card).not.toContain('class="featured-card-index"')
    expect(card).not.toContain('v-else class="ee-label font-mono text-[var(--ee-ink-faint)]"')
    expect(css).toContain('.article-card-index {')
    expect(css).toContain('font-size: 2.5rem;')
    expect(css).toContain('.article-card:hover .article-card-index {')
    expect(css).not.toContain('.featured-card-index')
  })
})
