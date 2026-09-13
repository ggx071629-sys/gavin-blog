import { readFileSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const webRoot = resolve(process.cwd())
const css = readFileSync(join(webRoot, 'assets', 'css', 'main.css'), 'utf8')
const nuxtConfig = readFileSync(join(webRoot, 'nuxt.config.ts'), 'utf8')
const markdownArticle = readFileSync(join(webRoot, 'components', 'MarkdownArticle.vue'), 'utf8')

const editorialProsePre = css.match(/\.prose-gavin\.editorial-prose pre\s*\{([^}]*)\}/)?.[1] ?? ''
const lightRoot = css.match(/:root\s*\{([\s\S]*?)\n\s*\}/)?.[1] ?? ''
const darkRoot = css.match(/:root\.dark\s*\{([\s\S]*?)\n\s*\}/)?.[1] ?? ''

describe('codeblock theme guardrails', () => {
  it('does not hardcode a dark background on editorial-prose pre', () => {
    expect(editorialProsePre).not.toContain('#0b0d12')
    expect(editorialProsePre).not.toContain('#0d1117')
    expect(editorialProsePre).toMatch(/background:\s*var\(--ee-/)
  })

  it('does not load a single hard-coded hljs dark theme globally', () => {
    expect(nuxtConfig).not.toContain('highlight.js/styles/github-dark.css')
    expect(nuxtConfig).not.toContain('highlight.js/styles/github.css')
  })

  it('keeps heavy article enhancers behind content-driven dynamic imports', () => {
    expect(markdownArticle).toContain("import hljs from 'highlight.js/lib/core'")
    expect(markdownArticle).not.toContain("import hljs from 'highlight.js'\n")
    expect(markdownArticle).not.toMatch(/^import .* from ['"](?:katex|markdown-it-texmath|mermaid)['"]/m)
    expect(markdownArticle).toContain("containsMath(content) && !mathEnabled")
    expect(nuxtConfig).not.toContain("'katex/dist/katex.min.css'")
    expect(markdownArticle).toContain("href: '/katex/katex.min.css'")
    expect(markdownArticle).toContain("import('katex')")
    expect(markdownArticle).toContain("import('markdown-it-texmath')")
    expect(markdownArticle).toContain("if (!nodes.length || renderId !== requestedRender) return")
    expect(markdownArticle).toContain("import('mermaid')")
    expect(markdownArticle).toContain("node.dataset.mermaidState = state")
    expect(markdownArticle).toContain("ini: () => import('highlight.js/lib/languages/ini')")
    expect(markdownArticle).toContain("toml: 'ini'")
  })

  it('defines hljs token color variables for the light theme', () => {
    expect(lightRoot).toMatch(/--hljs-text:/)
    expect(lightRoot).toMatch(/--hljs-keyword:/)
    expect(lightRoot).toMatch(/--hljs-string:/)
    expect(lightRoot).toMatch(/--hljs-comment:/)
    expect(lightRoot).toMatch(/--hljs-title:/)
    expect(lightRoot).toMatch(/--hljs-number:/)
  })

  it('defines hljs token color variables for the dark theme', () => {
    expect(darkRoot).toMatch(/--hljs-text:/)
    expect(darkRoot).toMatch(/--hljs-keyword:/)
    expect(darkRoot).toMatch(/--hljs-string:/)
    expect(darkRoot).toMatch(/--hljs-comment:/)
    expect(darkRoot).toMatch(/--hljs-title:/)
    expect(darkRoot).toMatch(/--hljs-number:/)
  })

  it('maps hljs token classes to the theme variables', () => {
    expect(css).toMatch(/\.hljs-keyword[^{]*\{[^}]*var\(--hljs-keyword\)/)
    expect(css).toMatch(/\.hljs-string[^{]*\{[^}]*var\(--hljs-string\)/)
    expect(css).toMatch(/\.hljs-comment[^{]*\{[^}]*var\(--hljs-comment\)/)
    expect(css).toMatch(/\.hljs-title[^{]*\{[^}]*var\(--hljs-title\)/)
    expect(css).toMatch(/\.hljs-number[^{]*\{[^}]*var\(--hljs-number\)/)
  })

  it('gives prose pre a theme-aware text color', () => {
    const prosePre = css.match(/\.prose-gavin pre\s*\{([^}]*)\}/)?.[1] ?? ''
    expect(prosePre).toMatch(/color:\s*var\(--ee-ink\)/)
  })
})
