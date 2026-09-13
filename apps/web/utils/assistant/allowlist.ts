const EXACT_PATHS = new Set([
  '/',
  '/articles',
  '/projects',
  '/books',
  '/archive',
  '/about',
  '/search',
])

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/
const YEAR_RE = /^\d{4}$/
const MONTH_RE = /^(0[1-9]|1[0-2])$/

export function isValidSlug(value: string): boolean {
  return value.length >= 1 && value.length <= 160 && SLUG_RE.test(value)
}

export function isAssistantLauncherPath(path: string): boolean {
  if (!path.startsWith('/') || path.includes('?') || path.includes('#') || path.includes('%')) {
    return false
  }
  if (path.includes('//') || path.includes('\\') || path.includes('.')) return false
  if (EXACT_PATHS.has(path)) return true
  const notes = path.match(/^\/notes\/([^/]+)\/([^/]+)\/([^/]+)$/)
  if (notes) {
    return YEAR_RE.test(notes[1]!) && MONTH_RE.test(notes[2]!) && isValidSlug(notes[3]!)
  }
  const project = path.match(/^\/projects\/([^/]+)$/)
  if (project) return isValidSlug(project[1]!)
  const book = path.match(/^\/books\/([^/]+)\/([^/]+)\/([^/]+)$/)
  if (book) {
    return YEAR_RE.test(book[1]!) && MONTH_RE.test(book[2]!) && isValidSlug(book[3]!)
  }
  return false
}

export function isNavigableSourcePath(path: string): boolean {
  if (!path.startsWith('/') || path.includes('?') || path.includes('#') || path.includes('%')) {
    return false
  }
  if (path.includes('//') || path.includes('\\') || path.includes('.') || path.includes(':')) {
    return false
  }
  if (path === '/' || path === '/about' || isResumeSourcePath(path)) return true
  const notes = path.match(/^\/notes\/([^/]+)\/([^/]+)\/([^/]+)$/)
  if (notes) {
    return YEAR_RE.test(notes[1]!) && MONTH_RE.test(notes[2]!) && isValidSlug(notes[3]!)
  }
  const project = path.match(/^\/projects\/([^/]+)$/)
  if (project) return isValidSlug(project[1]!)
  const book = path.match(/^\/books\/([^/]+)\/([^/]+)\/([^/]+)$/)
  if (book) {
    return YEAR_RE.test(book[1]!) && MONTH_RE.test(book[2]!) && isValidSlug(book[3]!)
  }
  return false
}

export function isResumeSourcePath(path: string): boolean {
  return /^\/api\/v1\/assistant\/resume\/[0-9a-f]{32}$/.test(path)
}
