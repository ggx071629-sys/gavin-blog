import type { WikiResolution } from '~/types/api'

const WIKILINK_RE = /\[\[([^[\]]+?)\]\]/g
const FENCE_RE = /^[ \t]*(```+|~~~+)[^\n]*\n[\s\S]*?^[ \t]*\1[ \t]*$/gm
const INLINE_CODE_RE = /`+[^`\n]+`+/g

export const maskCodeRegions = (content: string): string => (
  content
    .replace(FENCE_RE, match => match.replace(/[^\n]/g, ' '))
    .replace(INLINE_CODE_RE, match => match.replace(/[^\n]/g, ' '))
)

export const applyWikilinks = (content: string, resolutions: readonly WikiResolution[]): string => {
  if (!content || !resolutions.length) {
    return content.replace(WIKILINK_RE, (_match, raw: string, offset: number, source: string) => {
      if (maskCodeRegions(source)[offset] === ' ') return _match
      const display = parseWikilink(raw).display
      return display
    })
  }
  const byToken = new Map(resolutions.map(item => [item.token, item]))
  const masked = maskCodeRegions(content)
  return content.replace(WIKILINK_RE, (match, raw: string, offset: number) => {
    if (masked[offset] === ' ') return match
    const parsed = parseWikilink(raw)
    const resolved = byToken.get(parsed.token)
    if (resolved?.public_path) return `[${parsed.display}](${resolved.public_path})`
    return parsed.display
  })
}

export const parseWikilink = (raw: string): { token: string, display: string } => {
  const trimmed = raw.trim()
  const separator = trimmed.indexOf('|')
  if (separator === -1) return { token: trimmed, display: trimmed }
  const token = trimmed.slice(0, separator).trim()
  const display = trimmed.slice(separator + 1).trim()
  return { token, display: display || token }
}
