import { normalizeApiUpstream } from '~/utils/api-url'
import { isResumeSourcePath } from '~/utils/assistant/allowlist'
import {
  PROXY_SIGNATURE_HEADER,
  PROXY_TIMESTAMP_HEADER,
  resolveAssistantProxyClientIp,
  signAssistantProxyIdentity,
} from '~/server/utils/assistant-proxy-identity'

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  const requestUrl = getRequestURL(event)
  const upstream = normalizeApiUpstream(config.apiUpstream)
  const target = new URL(`${requestUrl.pathname}${requestUrl.search}`, upstream)
  const expectedOrigin = new URL(upstream).origin
  if (target.origin !== expectedOrigin) {
    throw createError({ statusCode: 502, statusMessage: 'Upstream origin mismatch' })
  }
  // Public immutable-version attachments need no chat identity or provider session.
  if (isResumeSourcePath(requestUrl.pathname) && event.method === 'GET' && !requestUrl.search && !requestUrl.hash) {
    return proxyRequest(event, target.toString(), { fetchOptions: { redirect: 'error' } })
  }
  if (!requestUrl.pathname.startsWith('/api/v1/assistant') && !requestUrl.pathname.startsWith('/api/v1/admin/assistant/trial/')) {
    return proxyRequest(event, target.toString(), { fetchOptions: { redirect: 'error' } })
  }
  const assistantPaths = new Set([
    '/api/v1/assistant/availability',
    '/api/v1/admin/assistant/trial/sessions',
    '/api/v1/admin/assistant/trial/session',
    '/api/v1/admin/assistant/trial/questions',
    '/api/v1/admin/assistant/trial/resume',
    '/api/v1/assistant/sessions',
    '/api/v1/assistant/session',
    '/api/v1/assistant/questions',
  ])
  const feedbackPath = event.method === 'PUT'
    && /^\/api\/v1\/assistant\/turns\/[0-9a-f]{32}\/feedback$/.test(requestUrl.pathname)
  if ((!assistantPaths.has(requestUrl.pathname) && !feedbackPath) || requestUrl.search || requestUrl.hash) {
    throw createError({ statusCode: 404, statusMessage: 'Unknown assistant endpoint' })
  }
  const method = event.method
  const headers = new Headers()
  const incoming = getRequestHeaders(event)
  for (const key of ['cookie', 'x-csrf-token', 'content-type', 'x-assistant-csrf', 'idempotency-key', 'last-event-id', 'origin', 'sec-fetch-site', 'sec-fetch-mode', 'accept']) {
    const value = incoming[key]
    if (value) headers.set(key, Array.isArray(value) ? value[0]! : value)
  }
  const browserHost = incoming.host
  if (browserHost) {
    headers.set('x-forwarded-host', Array.isArray(browserHost) ? browserHost[0]! : browserHost)
  }
  headers.set('x-forwarded-proto', requestUrl.protocol.replace(/:$/, ''))
  const edgeHeader = String(config.assistantEdgeClientIpHeader || '').toLowerCase()
  const apiHeader = String(config.assistantApiClientIpHeader || '')
  if (!edgeHeader || !apiHeader) {
    throw createError({ statusCode: 503, statusMessage: 'Assistant proxy identity disabled' })
  }
  let clientIp: string
  try {
    const incomingIdentity = incoming[edgeHeader]
    clientIp = resolveAssistantProxyClientIp({
      peerAddress: getRequestIP(event),
      requestHostname: requestUrl.hostname,
      trustedCidrs: String(config.assistantTrustedEdgeProxies || ''),
      edgeHeaderValue: Array.isArray(incomingIdentity) ? undefined : incomingIdentity,
      allowDirectLoopback: Boolean(config.assistantDevDirectLoopback),
    })
  } catch {
    throw createError({ statusCode: 400, statusMessage: 'Invalid assistant proxy identity' })
  }
  const timestamp = Math.floor(Date.now() / 1000)
  let signature: string
  try {
    signature = signAssistantProxyIdentity({
      secret: String(config.assistantProxyHmacSecret || ''),
      method,
      path: requestUrl.pathname,
      clientIp,
      timestamp,
    })
  } catch {
    throw createError({ statusCode: 503, statusMessage: 'Assistant proxy identity disabled' })
  }
  headers.set(apiHeader, clientIp)
  headers.set(PROXY_TIMESTAMP_HEADER, String(timestamp))
  headers.set(PROXY_SIGNATURE_HEADER, signature)
  const rawBody = method === 'GET' || method === 'HEAD' ? undefined : await readRawBody(event)
  const response = await fetch(target, {
    method,
    headers,
    body: rawBody,
    redirect: 'error',
  })
  const actual = new URL(response.url)
  if (
    actual.origin !== expectedOrigin
    || actual.pathname !== target.pathname
    || actual.search !== ''
    || actual.hash !== ''
  ) {
    throw createError({ statusCode: 502, statusMessage: 'Upstream redirect rejected' })
  }
  setResponseStatus(event, response.status)
  const cache = response.headers.get('cache-control')
  if (cache) setResponseHeader(event, 'cache-control', cache)
  const retry = response.headers.get('retry-after')
  if (retry) event.node.res.setHeader('retry-after', retry)
  const type = response.headers.get('content-type')
  if (type) setResponseHeader(event, 'content-type', type)
  setResponseHeader(event, 'x-accel-buffering', 'no')
  if (response.ok && requestUrl.pathname.endsWith('/questions') && !(type || '').toLowerCase().startsWith('text/event-stream')) {
    throw createError({ statusCode: 502, statusMessage: 'Non-stream assistant response' })
  }
  for (const cookie of response.headers.getSetCookie()) {
    appendResponseHeader(event, 'set-cookie', cookie)
  }
  return response.body
})
