const RELATIVE_API_BASE = '/api/v1'

export function sameOriginApiBase(apiBase: string, origin: string): boolean {
  if (typeof apiBase !== 'string' || typeof origin !== 'string') return false
  if (apiBase !== RELATIVE_API_BASE) return false
  if (!/^https?:\/\//i.test(origin)) return false
  try {
    const resolved = new URL(apiBase, origin)
    return resolved.origin === origin && resolved.pathname === RELATIVE_API_BASE
  }
  catch {
    return false
  }
}
