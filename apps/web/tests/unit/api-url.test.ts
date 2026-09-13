import { describe, expect, it } from 'vitest'
import { normalizeApiUpstream, resolvePublicUrl, serverApiBase } from '../../utils/api-url'

describe('same-origin API URL helpers', () => {
  it('normalizes an HTTP(S) upstream to an origin', () => {
    expect(normalizeApiUpstream('http://127.0.0.1:8000/')).toBe('http://127.0.0.1:8000')
    expect(serverApiBase('https://api.example.test/path')).toBe('https://api.example.test/api/v1')
  })

  it('rejects unsafe or credential-bearing upstreams', () => {
    expect(() => normalizeApiUpstream('file:///tmp/api')).toThrow('HTTP(S)')
    expect(() => normalizeApiUpstream('https://user:secret@example.test')).toThrow('credentials')
  })

  it('keeps external media absolute and local media same-origin', () => {
    expect(resolvePublicUrl('https://cdn.example.test/image.webp')).toBe('https://cdn.example.test/image.webp')
    expect(resolvePublicUrl('/api/v1/media/1/webp')).toBe('/api/v1/media/1/webp')
    expect(resolvePublicUrl('api/v1/media/1/webp')).toBe('/api/v1/media/1/webp')
  })
})
