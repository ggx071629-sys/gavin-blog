import MarkdownIt from 'markdown-it'

export interface MarkdownHeading {
  level: 2 | 3
  title: string
  slug: string
}

const markdown = new MarkdownIt()
export const slugifyMarkdownHeading = (value: string) =>
  encodeURIComponent(value.trim().toLowerCase().replace(/\s+/g, '-'))

export function normalizeStandaloneNotices(content: string): string {
  return content.replace(
    /(^|\n\n)提示[ \t]*\n\n((?:(?!\n\n)[\s\S])+)(?=\n\n|$)/g,
    (_match, prefix: string, body: string) => `${prefix}::: note\n**提示**\n\n${body.trim()}\n:::`,
  )
}

export function extractMarkdownHeadings(content: string): MarkdownHeading[] {
  const tokens = markdown.parse(content, {})
  const seen = new Map<string, number>()
  const headings: MarkdownHeading[] = []

  for (let index = 0; index < tokens.length; index += 1) {
    const token = tokens[index]
    if (token?.type !== 'heading_open' || (token.tag !== 'h1' && token.tag !== 'h2')) continue
    const inline = tokens[index + 1]
    const title = inline?.children
      ?.filter(child => child.type === 'text' || child.type === 'code_inline')
      .map(child => child.content)
      .join('')
      .trim()
    if (!title) continue
    const base = slugifyMarkdownHeading(title)
    const occurrence = seen.get(base) || 0
    seen.set(base, occurrence + 1)
    headings.push({
      level: token.tag === 'h1' ? 2 : 3,
      title,
      slug: occurrence === 0 ? base : `${base}-${occurrence}`,
    })
  }

  return headings
}

export function markdownToPlainText(content: string): string {
  const tokens = markdown.parse(content, {})
  const parts: string[] = []

  for (const token of tokens) {
    if (token.type !== 'inline') continue
    for (const child of token.children || []) {
      if (child.type === 'text' || child.type === 'code_inline' || child.type === 'image') {
        parts.push(child.content)
      }
      else if (child.type === 'softbreak' || child.type === 'hardbreak') {
        parts.push(' ')
      }
    }
  }

  return parts
    .join(' ')
    .replace(/\s+/g, ' ')
    .replace(/\s+([，。！？；：、）】])/g, '$1')
    .replace(/([（【])\s+/g, '$1')
    .trim()
}

export function articleDescription(summary: string, content: string, maxLength = 180): string {
  const source = markdownToPlainText(summary).trim() || markdownToPlainText(content).trim()
  if (!source) return 'Gavin 的技术文章、问题排查与项目复盘。'
  if (source.length <= maxLength) return source
  return `${source.slice(0, Math.max(1, maxLength - 1)).trimEnd()}…`
}

export interface FenceInfo {
  language: string
  filename: string | null
}

export function parseFenceInfo(info: string): FenceInfo {
  const tokens = info.trim().split(/\s+/).filter(Boolean)
  const language = tokens[0] || ''
  if (tokens.length < 2) return { language, filename: null }
  const rest = tokens.slice(1).join(' ')
  if (rest.startsWith('{')) return { language, filename: null }
  return { language, filename: rest }
}

export interface LeadFigure {
  src: string
  alt: string
  content: string
}

export function isSafeMediaSrc(src: string): boolean {
  return /^(https?:\/\/|\/)[^\s]+$/i.test(src) && !/^javascript:/i.test(src)
}

export function stripMatchingTitleHeading(content: string, title: string): string {
  const expected = title.trim()
  if (!expected) return content
  const lines = content.replace(/^\uFEFF/, '').split('\n')
  let index = 0
  while (index < lines.length && lines[index]?.trim() === '') index += 1
  const match = lines[index]?.match(/^#\s+(.+)$/)
  const heading = match?.[1]
  if (!heading || heading.trim() !== expected) return content
  return [...lines.slice(0, index), ...lines.slice(index + 1)].join('\n').replace(/^\n+/, '')
}

export function extractLeadFigure(content: string): LeadFigure | null {
  const lines = content.replace(/^\uFEFF/, '').split('\n')
  let index = 0
  while (index < lines.length && lines[index]?.trim() === '') index += 1
  if (index < lines.length && /^#\s+\S/.test(lines[index] || '') && !lines[index]?.startsWith('##')) {
    index += 1
    while (index < lines.length && lines[index]?.trim() === '') index += 1
  }
  const line = lines[index]
  if (!line) return null
  const match = line.trim().match(/^!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)$/)
  if (!match) return null
  const alt = match[1] || ''
  const src = match[2] || ''
  if (!src || !isSafeMediaSrc(src)) return null
  const remaining = [...lines.slice(0, index), ...lines.slice(index + 1)].join('\n')
  return { src, alt, content: remaining.replace(/\n{3,}/g, '\n\n').replace(/^\n+/, '') }
}
