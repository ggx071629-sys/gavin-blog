import { isNavigableSourcePath } from './allowlist'

export type AssistantCitation = {
  n: string
  title: string
  path: string
  heading_path?: string
  alias?: string
}

export type AssistantSource = {
  n: string
  title: string
  path: string
  heading_path?: string
}

const MARKER_RE = /\[([1-9][0-9]*)\]/g
const ARRAY_RE = /[A-Za-z_][A-Za-z0-9_]*\s*(?:\[\s*\d+\s*\])+/g
const INLINE_CODE_RE = /`([^`\n]*)`/g
const DECIMAL_RE = /^[1-9][0-9]*$/

function* answerMarkers(text: string) {
  const arrays = [...text.matchAll(INLINE_CODE_RE)]
    .filter(match => (match[1] ?? '').match(ARRAY_RE))
    .map(match => [match.index ?? 0, (match.index ?? 0) + match[0].length] as const)
  for (const match of text.matchAll(MARKER_RE)) {
    const at = match.index ?? 0
    // The API explicitly wraps literal arrays. Unwrapped markers keep their
    // original meaning, including legacy "Certbot[1]. Renewal[2]" answers.
    if (arrays.some(([start, end]) => at >= start && at < end)) continue
    yield match
  }
}

export const displayLiteral = (text: string) => text.replace(INLINE_CODE_RE,
  (span: string, body: string) => body.match(ARRAY_RE) ? body : span)

const onlyKeys = (row: Record<string, unknown>, allowed: string[]) =>
  Object.keys(row).every(key => allowed.includes(key))

export function splitAnswerMarkers(text: string): { text?: string, marker?: string }[] {
  const parts: { text?: string, marker?: string }[] = []
  let last = 0
  for (const match of answerMarkers(text)) {
    const start = match.index ?? 0
    if (start > last) parts.push({ text: displayLiteral(text.slice(last, start)) })
    parts.push({ marker: match[1] })
    last = start + match[0].length
  }
  if (last < text.length) parts.push({ text: displayLiteral(text.slice(last)) })
  return parts
}

export function closeAnswerCitations(
  answer: string,
  citations: unknown,
  sources: unknown,
): { paragraphs: string[], markers: { n: string, citation: AssistantCitation }[], sources: AssistantSource[] } | null {
  if (typeof answer !== 'string' || !answer.trim()) return null
  if (!Array.isArray(citations) || !Array.isArray(sources)) return null
  const typedCitations: AssistantCitation[] = []
  for (const item of citations) {
    if (!item || typeof item !== 'object') return null
    const row = item as Record<string, unknown>
    if (!onlyKeys(row, ['n', 'alias', 'title', 'heading_path', 'path'])) return null
    if (typeof row.n !== 'string' || !DECIMAL_RE.test(row.n) || typeof row.title !== 'string' || typeof row.path !== 'string') return null
    if (row.alias !== undefined && row.alias !== null && typeof row.alias !== 'string') return null
    if (row.heading_path !== undefined && row.heading_path !== null && typeof row.heading_path !== 'string') return null
    if (!isNavigableSourcePath(row.path)) return null
    typedCitations.push({
      n: row.n,
      title: row.title,
      path: row.path,
      heading_path: typeof row.heading_path === 'string' ? row.heading_path : undefined,
      alias: typeof row.alias === 'string' ? row.alias : undefined,
    })
  }
  const typedSources: AssistantSource[] = []
  for (const item of sources) {
    if (!item || typeof item !== 'object') return null
    const row = item as Record<string, unknown>
    if (!onlyKeys(row, ['n', 'title', 'heading_path', 'path'])) return null
    if (typeof row.n !== 'string' || !DECIMAL_RE.test(row.n) || typeof row.title !== 'string' || typeof row.path !== 'string') return null
    if (row.heading_path !== undefined && row.heading_path !== null && typeof row.heading_path !== 'string') return null
    if (!isNavigableSourcePath(row.path)) return null
    typedSources.push({
      n: row.n,
      title: row.title,
      path: row.path,
      heading_path: typeof row.heading_path === 'string' ? row.heading_path : undefined,
    })
  }
  const citationByN = new Map<string, AssistantCitation>()
  for (const citation of typedCitations) {
    const existing = citationByN.get(citation.n)
    if (existing && (existing.path !== citation.path || existing.title !== citation.title)) return null
    citationByN.set(citation.n, citation)
  }
  for (const source of typedSources) {
    const citation = typedCitations.find(item => item.n === source.n && item.path === source.path && item.title === source.title)
    if (!citation) return null
  }
  const markers: { n: string, citation: AssistantCitation }[] = []
  const used = new Set<string>()
  for (const match of answerMarkers(answer)) {
    const n = match[1]!
    const citation = citationByN.get(n)
    if (!citation) return null
    // The API numbers evidence chunks, but deduplicates sources by public path.
    if (!typedSources.some(source => source.path === citation.path && source.title === citation.title)) return null
    if (!used.has(n)) {
      markers.push({ n, citation })
      used.add(n)
    }
  }
  return {
    paragraphs: answer.split(/\n\n/),
    markers,
    sources: typedSources,
  }
}
