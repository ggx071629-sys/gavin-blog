export function normalizeApiUpstream(value: string): string {
  const upstream = new URL(value)
  if (!['http:', 'https:'].includes(upstream.protocol)) {
    throw new Error('API upstream must use HTTP(S)')
  }
  if (upstream.username || upstream.password) {
    throw new Error('API upstream must not contain credentials')
  }
  return upstream.origin
}

export function serverApiBase(value: string): string {
  return `${normalizeApiUpstream(value)}/api/v1`
}

export function resolvePublicUrl(value: string): string {
  if (/^https?:\/\//i.test(value)) return value
  return value.startsWith('/') ? value : `/${value}`
}
