import { describe, expect, it } from 'vitest'
import {
  ipInCidr,
  resolveAssistantProxyClientIp,
  resolveTrustedEdgeClientIp,
  signAssistantProxyIdentity,
} from '../../server/utils/assistant-proxy-identity'

describe('assistant trusted proxy identity', () => {
  it('matches IPv4, mapped IPv4, and IPv6 CIDRs exactly', () => {
    expect(ipInCidr('127.0.0.1', '127.0.0.0/8')).toBe(true)
    expect(ipInCidr('10.4.5.6', '10.4.0.0/16')).toBe(true)
    expect(ipInCidr('10.5.5.6', '10.4.0.0/16')).toBe(false)
    expect(ipInCidr('::1', '::1/128')).toBe(true)
  })

  it('accepts one edge-produced address only from a trusted socket peer', () => {
    expect(resolveTrustedEdgeClientIp({
      peerAddress: '::ffff:127.0.0.1',
      trustedCidrs: '127.0.0.1/32',
      edgeHeaderValue: '198.51.100.24',
    })).toBe('198.51.100.24')

    expect(() => resolveTrustedEdgeClientIp({
      peerAddress: '192.0.2.20',
      trustedCidrs: '127.0.0.1/32',
      edgeHeaderValue: '198.51.100.24',
    })).toThrow('trusted edge peer')
  })

  it('rejects missing and chained browser identities', () => {
    expect(() => resolveTrustedEdgeClientIp({
      peerAddress: '127.0.0.1',
      trustedCidrs: '127.0.0.1/32',
      edgeHeaderValue: undefined,
    })).toThrow('identity is missing')
    expect(() => resolveTrustedEdgeClientIp({
      peerAddress: '127.0.0.1',
      trustedCidrs: '127.0.0.1/32',
      edgeHeaderValue: '198.51.100.24, 203.0.113.7',
    })).toThrow('identity is missing')
  })

  it('allows a missing edge header only for the explicit trusted loopback development seam', () => {
    expect(resolveAssistantProxyClientIp({
      peerAddress: '::ffff:127.0.0.1',
      trustedCidrs: '127.0.0.1/32',
      edgeHeaderValue: undefined,
      allowDirectLoopback: true,
    })).toBe('127.0.0.1')

    expect(() => resolveAssistantProxyClientIp({
      peerAddress: '127.0.0.1',
      trustedCidrs: '127.0.0.1/32',
      edgeHeaderValue: undefined,
      allowDirectLoopback: false,
    })).toThrow('identity is missing')

    expect(() => resolveAssistantProxyClientIp({
      peerAddress: '192.0.2.20',
      trustedCidrs: '127.0.0.1/32',
      edgeHeaderValue: undefined,
      allowDirectLoopback: true,
    })).toThrow('trusted edge peer')

    expect(resolveAssistantProxyClientIp({
      peerAddress: undefined,
      requestHostname: '127.0.0.1',
      trustedCidrs: '127.0.0.1/32,::1/128',
      edgeHeaderValue: undefined,
      allowDirectLoopback: true,
    })).toBe('127.0.0.1')

    expect(() => resolveAssistantProxyClientIp({
      peerAddress: undefined,
      requestHostname: 'localhost',
      trustedCidrs: '127.0.0.1/32,::1/128',
      edgeHeaderValue: undefined,
      allowDirectLoopback: true,
    })).toThrow('edge peer address is missing')
  })

  it('binds the signature to method, path, address, and timestamp', () => {
    const options = {
      secret: 'assistant-proxy-secret-value-32bytes',
      method: 'POST',
      path: '/api/v1/assistant/questions',
      clientIp: '198.51.100.24',
      timestamp: 1788051600,
    }
    const first = signAssistantProxyIdentity(options)
    expect(first).toMatch(/^[0-9a-f]{64}$/)
    expect(signAssistantProxyIdentity(options)).toBe(first)
    expect(signAssistantProxyIdentity({ ...options, path: '/api/v1/assistant/session' }))
      .not.toBe(first)
  })
})
