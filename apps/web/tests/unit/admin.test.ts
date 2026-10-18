import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { join, relative, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { ADMIN_NAV_GROUPS, isAdminNavItemActive } from '../../utils/admin'

const webRoot = resolve(process.cwd())
const adminPagesRoot = join(webRoot, 'pages', 'admin')
const componentsRoot = join(webRoot, 'components')
const rawPaletteClass = /(?:^|[\s'"`])(?:[\w-]+:)*(?:bg|text|border|divide|ring|outline)-(?:slate|gray|blue|sky|purple|rose|red|amber|emerald|green)-\d+(?:\/\d+)?(?=$|[\s'"`])/g

const vueFilesUnder = (directory: string): string[] => readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
  const path = join(directory, entry.name)
  if (entry.isDirectory()) return vueFilesUnder(path)
  return entry.name.endsWith('.vue') ? [path] : []
})

const templateSource = (source: string) => source.match(/<template>([\s\S]*?)<\/template>/)?.[1] ?? ''

const relativeLuminance = (hex: string) => {
  const pairs = hex.match(/[\da-f]{2}/gi)
  if (pairs?.length !== 3) throw new Error(`Invalid hex color: ${hex}`)
  const channels = pairs.map(value => Number.parseInt(value, 16) / 255) as [number, number, number]
  const [red, green, blue] = channels.map(value => value <= 0.04045
    ? value / 12.92
    : ((value + 0.055) / 1.055) ** 2.4) as [number, number, number]
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue
}

const contrastRatio = (first: string, second: string) => {
  const luminances = [relativeLuminance(first), relativeLuminance(second)]
  const lighter = Math.max(...luminances)
  const darker = Math.min(...luminances)
  return (lighter + 0.05) / (darker + 0.05)
}

describe('admin navigation', () => {
  it('keeps every existing admin destination in the core navigation', () => {
    expect(ADMIN_NAV_GROUPS.flatMap(group => group.items.map(item => item.href))).toEqual([
      '/admin/articles',
      '/admin/books',
      '/admin/projects',
      '/admin/profile',
      '/admin/account',
      '/admin/about',
      '/admin/taxonomy',
      '/admin/media',
      '/admin/content',
      '/admin/assistant',
    ])
  })

  it('marks nested editor routes active without matching similar prefixes', () => {
    expect(isAdminNavItemActive('/admin/articles/42/edit', '/admin/articles')).toBe(true)
    expect(isAdminNavItemActive('/admin/articles', '/admin/articles')).toBe(true)
    expect(isAdminNavItemActive('/admin/articles-extra', '/admin/articles')).toBe(false)
    expect(isAdminNavItemActive('/admin/projects', '/admin/articles')).toBe(false)
  })
})

describe('electric editorial hardening guardrails', () => {
  it('keeps raw Tailwind palette classes out of admin and shared component templates', () => {
    const violations = [...vueFilesUnder(adminPagesRoot), ...vueFilesUnder(componentsRoot)].flatMap((path) => {
      const matches = templateSource(readFileSync(path, 'utf8')).match(rawPaletteClass) ?? []
      return matches.map(match => `${relative(webRoot, path)}: ${match.trim()}`)
    })

    expect(violations).toEqual([])
  })

  it('prevents substring compatibility selectors and duplicate admin status tokens', () => {
    const css = readFileSync(join(webRoot, 'assets', 'css', 'main.css'), 'utf8')
    expect(css).not.toMatch(/\[class\*=/)
    expect(css).not.toMatch(/--admin-(?:warning|danger)/)
    for (const token of ['canvas', 'surface', 'surface-low', 'surface-high', 'ink', 'ink-muted', 'ink-faint', 'line', 'line-soft', 'primary', 'signal', 'focus']) {
      expect(css, `missing --ee-${token}`).toContain(`--ee-${token}:`)
    }
    for (const state of ['info', 'success', 'warning', 'danger']) {
      for (const role of ['bg', 'border', 'ink']) expect(css, `missing --ee-${state}-${role}`).toContain(`--ee-${state}-${role}:`)
    }
  })

  it('keeps admin-core as the only protected admin shell', () => {
    expect(existsSync(join(webRoot, 'layouts', 'admin.vue'))).toBe(false)
    const legacyReferences = vueFilesUnder(adminPagesRoot).filter(path => /layout:\s*['"]admin['"]/.test(readFileSync(path, 'utf8')))
    expect(legacyReferences).toEqual([])
  })

  it('keeps SSR theme colors synchronized with the canvas tokens', () => {
    const css = readFileSync(join(webRoot, 'assets', 'css', 'main.css'), 'utf8')
    const config = readFileSync(join(webRoot, 'nuxt.config.ts'), 'utf8')
    expect(css).toContain('--ee-canvas: #f3f5f9;')
    expect(css).toMatch(/:root\.dark[\s\S]*?--ee-canvas: #07080c;/)
    expect(config).toContain("content: '#f3f5f9', media: '(prefers-color-scheme: light)'")
    expect(config).toContain("content: '#07080c', media: '(prefers-color-scheme: dark)'")
  })

  it('keeps one accent per theme with accessible signal contrast', () => {
    const css = readFileSync(join(webRoot, 'assets', 'css', 'main.css'), 'utf8')
    const lightTokens = css.match(/:root\s*{([\s\S]*?)\n\s*}/)?.[1] ?? ''
    const darkTokens = css.match(/:root\.dark\s*{([\s\S]*?)\n\s*}/)?.[1] ?? ''

    expect(lightTokens).toContain('--ee-signal: #0b5cff;')
    expect(lightTokens).toContain('--ee-signal-ink: #ffffff;')
    expect(darkTokens).toContain('--ee-signal: #c9f24b;')
    expect(darkTokens).toContain('--ee-signal-ink: #101500;')
    expect(contrastRatio('#0b5cff', '#f3f5f9')).toBeGreaterThanOrEqual(3)
    expect(contrastRatio('#0b5cff', '#ffffff')).toBeGreaterThanOrEqual(4.5)
    expect(contrastRatio('#c9f24b', '#07080c')).toBeGreaterThanOrEqual(3)
    expect(contrastRatio('#c9f24b', '#101500')).toBeGreaterThanOrEqual(4.5)
  })
})
