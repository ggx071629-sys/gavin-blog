import { readFileSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const webRoot = resolve(process.cwd())

describe('theme typography guardrails', () => {
  it('hosts Noto Sans SC 400/700 and Inter without Hanken or Google Fonts', () => {
    const css = readFileSync(join(webRoot, 'assets', 'css', 'main.css'), 'utf8')
    const config = readFileSync(join(webRoot, 'nuxt.config.ts'), 'utf8')
    const packageJson = readFileSync(join(webRoot, 'package.json'), 'utf8')
    const lightTokens = css.match(/:root\s*{([\s\S]*?)\n\s*}/)?.[1] ?? ''
    const darkTokens = css.match(/:root\.dark\s*{([\s\S]*?)\n\s*}/)?.[1] ?? ''
    const headingStack = '--ee-heading: "Space Grotesk", Inter, "Noto Sans SC", ui-sans-serif, system-ui, sans-serif;'

    expect(lightTokens).toContain(headingStack)
    expect(darkTokens).not.toContain('--ee-heading:')
    expect(config).toContain("'@fontsource/inter/latin-400.css'")
    expect(config).toContain("'@fontsource/inter/latin-700.css'")
    expect(config).toContain("'@fontsource/space-grotesk/latin-500.css'")
    expect(config).toContain("'@fontsource/space-grotesk/latin-700.css'")
    expect(config).toContain("'@fontsource/noto-sans-sc/chinese-simplified-400.css'")
    expect(config).toContain("'@fontsource/noto-sans-sc/chinese-simplified-700.css'")
    expect(config).toContain("'@fontsource/jetbrains-mono/latin-400.css'")
    expect(config).not.toContain('hanken-grotesk')
    expect(config).not.toContain('latin-800')
    expect(config).not.toContain('chinese-simplified-800')
    expect(config).not.toContain('fonts.googleapis.com')
    expect(config).not.toContain('fonts.gstatic.com')
    expect(config).not.toContain('family=Chivo')
    expect(packageJson).toContain('"@fontsource/noto-sans-sc"')
    expect(packageJson).toContain('"@fontsource/space-grotesk"')
    expect(packageJson).not.toContain('hanken-grotesk')
    expect(css).not.toContain('Hanken Grotesk')
  })

  it('keeps homepage empty-state copy in the shipped template', () => {
    const home = readFileSync(join(webRoot, 'pages', 'index.vue'), 'utf8')
    expect(home).toContain('第一篇文章正在路上。')
    expect(home).not.toContain('data-testid="home-now"')
    expect(home).toContain('<HomeNotebookHero')
    const hero = readFileSync(join(webRoot, 'components', 'HomeNotebookHero.vue'), 'utf8')
    expect(hero).toMatch(/<NuxtLink to="\/articles"[^>]*>浏览文章/)
    expect(hero).toMatch(/<NuxtLink to="\/projects"[^>]*>查看项目/)
  })
})
