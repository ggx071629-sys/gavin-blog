import { readFileSync, readdirSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const webRoot = resolve(process.cwd())
const css = readFileSync(join(webRoot, 'assets', 'css', 'main.css'), 'utf8')

const themeBlock = (selector: string) => css.match(new RegExp(`${selector}\\s*\\{([\\s\\S]*?)\\n\\s*\\}`))?.[1] ?? ''

const vueFiles = (directory: string): string[] => readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
  const path = join(directory, entry.name)
  if (entry.isDirectory()) return vueFiles(path)
  return entry.isFile() && entry.name.endsWith('.vue') ? [path] : []
})

const structuralUtility = /^(?:p[trblxy]?-\d|m[trblxy]?-\d|gap(?:-[xy])?-\d|grid(?:-.+)?|flex(?:-.+)?|block|hidden|inline(?:-.+)?|col-.+|row-.+|w-.+|h-.+|min-[wh]-.+|max-[wh]-.+|rounded(?:-.+)?|shadow(?:-.+)?|overflow-.+|items-.+|justify-.+|order-.+|space-[xy]-.+|border(?:-\d+|-[trblxy](?:-\d+)?)?)$/

describe('theme structure guardrails', () => {
  it('shares the dark shape scale and elevation geometry across themes', () => {
    const lightTokens = themeBlock(':root')
    const darkTokens = themeBlock(':root\\.dark')

    expect(lightTokens).toContain('--ee-radius: 4px;')
    expect(lightTokens).toContain('--ee-radius-soft: 8px;')
    expect(lightTokens).toMatch(/--ee-floating-shadow: 0 18px 45px/)
    expect(darkTokens).not.toContain('--ee-radius:')
    expect(darkTokens).not.toContain('--ee-radius-soft:')
    expect(darkTokens).toMatch(/--ee-floating-shadow: 0 18px 45px/)
  })

  it('does not keep public layout rules behind light or dark selectors', () => {
    expect(css).not.toMatch(/\.dark\s+\.home-/)
    expect(css).not.toContain(':root:not(.dark) .article-card-list')
    expect(css).not.toMatch(/(?:\.dark\s+|:root:not\(\.dark\)\s+)\.search-/)
  })

  it('pairs every theme-specific Vue structural utility with the same base utility', () => {
    const violations: string[] = []

    for (const file of vueFiles(webRoot)) {
      const source = readFileSync(file, 'utf8')
      for (const match of source.matchAll(/(?:class|:class)="([^"]+)"/g)) {
        const tokens = match[1]!.split(/\s+/).filter(Boolean)
        for (const token of tokens.filter(token => token.startsWith('dark:'))) {
          const base = token.slice('dark:'.length)
          if (structuralUtility.test(base) && !tokens.includes(base)) {
            violations.push(`${file.replace(`${webRoot}\\`, '')}: ${token}`)
          }
        }
      }
    }

    expect(violations).toEqual([])
  })

  it('keeps theme icon DOM and public profile handlers stable during SSR hydration', () => {
    const siteHeader = readFileSync(join(webRoot, 'components', 'SiteHeader.vue'), 'utf8')
    const adminToggle = readFileSync(join(webRoot, 'components', 'AdminThemeToggle.vue'), 'utf8')
    const home = readFileSync(join(webRoot, 'pages', 'index.vue'), 'utf8')
    const layout = readFileSync(join(webRoot, 'layouts', 'default.vue'), 'utf8')

    expect(siteHeader).not.toMatch(/v-(?:if|else).*colorMode\.value/)
    expect(adminToggle).not.toMatch(/v-(?:if|else).*colorMode\.value/)
    expect(home).toContain('usePublicProfile()')
    expect(layout).toContain('usePublicProfile()')
    expect(home).not.toContain("useAsyncData('public-profile'")
    expect(layout).not.toContain("useAsyncData('public-profile'")
  })
})
