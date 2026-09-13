import { createHmac } from 'node:crypto'
import { isIP } from 'node:net'

export const PROXY_TIMESTAMP_HEADER = 'x-gavin-client-ip-timestamp'
export const PROXY_SIGNATURE_HEADER = 'x-gavin-client-ip-signature'

type ParsedIp = { bits: 32 | 128, value: bigint, text: string }

function normalizeMappedIpv4(value: string): string {
  const text = value.trim().toLowerCase().split('%', 1)[0]!
  return text.startsWith('::ffff:') && isIP(text.slice(7)) === 4 ? text.slice(7) : text
}

function parseIpv4(value: string): ParsedIp {
  const parts = value.split('.').map(part => Number.parseInt(part, 10))
  if (parts.length !== 4 || parts.some(part => !Number.isInteger(part) || part < 0 || part > 255)) {
    throw new Error('invalid IPv4 address')
  }
  let result = 0n
  for (const part of parts) result = (result << 8n) | BigInt(part)
  return { bits: 32, value: result, text: parts.join('.') }
}

function parseIpv6(value: string): ParsedIp {
  let text = value.toLowerCase().split('%', 1)[0]!
  if (text.includes('.')) {
    const lastColon = text.lastIndexOf(':')
    const ipv4 = parseIpv4(text.slice(lastColon + 1)).value
    text = `${text.slice(0, lastColon)}:${(ipv4 >> 16n).toString(16)}:${(ipv4 & 0xffffn).toString(16)}`
  }
  const halves = text.split('::')
  if (halves.length > 2) throw new Error('invalid IPv6 address')
  const left = halves[0] ? halves[0].split(':') : []
  const right = halves.length === 2 && halves[1] ? halves[1].split(':') : []
  const missing = 8 - left.length - right.length
  if ((halves.length === 1 && missing !== 0) || missing < 0) throw new Error('invalid IPv6 address')
  const groups = [...left, ...Array.from({ length: missing }, () => '0'), ...right]
  if (groups.length !== 8) throw new Error('invalid IPv6 address')
  let result = 0n
  for (const group of groups) {
    if (!/^[0-9a-f]{1,4}$/.test(group)) throw new Error('invalid IPv6 address')
    result = (result << 16n) | BigInt(`0x${group}`)
  }
  return { bits: 128, value: result, text }
}

export function parseIp(value: string): ParsedIp {
  const normalized = normalizeMappedIpv4(value)
  const family = isIP(normalized)
  if (family === 4) return parseIpv4(normalized)
  if (family === 6) return parseIpv6(normalized)
  throw new Error('client IP is malformed')
}

export function ipInCidr(ip: string, cidr: string): boolean {
  const parsed = parseIp(ip)
  const [networkText, rawPrefix] = cidr.trim().split('/')
  const network = parseIp(networkText || '')
  if (parsed.bits !== network.bits) return false
  const prefix = rawPrefix === undefined ? parsed.bits : Number.parseInt(rawPrefix, 10)
  if (!Number.isInteger(prefix) || prefix < 0 || prefix > parsed.bits) {
    throw new Error('trusted proxy CIDR is malformed')
  }
  const shift = BigInt(parsed.bits - prefix)
  return (parsed.value >> shift) === (network.value >> shift)
}

export function resolveTrustedEdgeClientIp(options: {
  peerAddress: string | undefined
  trustedCidrs: string
  edgeHeaderValue: string | undefined
}): string {
  if (!options.peerAddress) throw new Error('edge peer address is missing')
  const peer = parseIp(options.peerAddress)
  const cidrs = options.trustedCidrs.split(',').map(value => value.trim()).filter(Boolean)
  if (!cidrs.length || !cidrs.some(cidr => ipInCidr(peer.text, cidr))) {
    throw new Error('assistant request did not arrive from a trusted edge peer')
  }
  const raw = options.edgeHeaderValue?.trim()
  if (!raw || raw.includes(',')) throw new Error('trusted edge client identity is missing')
  return parseIp(raw).text
}

export function resolveAssistantProxyClientIp(options: {
  peerAddress: string | undefined
  requestHostname?: string
  trustedCidrs: string
  edgeHeaderValue: string | undefined
  allowDirectLoopback: boolean
}): string {
  const requestLoopback = options.allowDirectLoopback && options.requestHostname === '127.0.0.1'
    ? options.requestHostname
    : undefined
  const peerAddress = options.peerAddress || requestLoopback
  return resolveTrustedEdgeClientIp({
    peerAddress,
    trustedCidrs: options.trustedCidrs,
    edgeHeaderValue: options.edgeHeaderValue
      || (options.allowDirectLoopback ? peerAddress : undefined),
  })
}

export function signAssistantProxyIdentity(options: {
  secret: string
  method: string
  path: string
  clientIp: string
  timestamp: number
}): string {
  if (options.secret.length < 32) throw new Error('assistant proxy HMAC secret is missing')
  const payload = [
    options.method.toUpperCase(),
    options.path,
    options.clientIp,
    String(options.timestamp),
  ].join('\n')
  return createHmac('sha256', options.secret)
    .update(`assistant-proxy-identity-v1|${payload}`, 'utf8')
    .digest('hex')
}
