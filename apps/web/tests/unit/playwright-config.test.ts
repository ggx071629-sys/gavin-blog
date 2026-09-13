import { readFileSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { E2E_API_PORT, resolveE2EWebPort } from '../support/e2e-env'

const webRoot = resolve(process.cwd())
const read = (name: string) => readFileSync(join(webRoot, name), 'utf8')

describe('playwright dev servers', () => {
  it('keeps isolated worktree servers independent from local state', () => {
    const e2e = read('playwright.config.ts')
    const authProxy = read('tests/e2e/auth-proxy.spec.ts')
    const failure = read('playwright.failure.config.ts')
    const nuxt = read('nuxt.config.ts')
    const e2eRunner = read('scripts/run-playwright-e2e.mjs')
    const assistantApiRunner = read('../api/scripts/run_assistant_e2e.py')
    const assistantProxyRoute = read('server/routes/api/v1/[...path].ts')

    expect(nuxt).toContain("typeCheck: process.env.NUXT_TYPECHECK !== '0'")
    expect(nuxt).toContain("strict: process.env.NUXT_VITE_FS_STRICT !== '0'")
    expect(nuxt).toContain("target: 'es2022'")
    expect(nuxt).toContain("'vite:extendConfig'")
    expect(e2e).toContain("NUXT_TYPECHECK: '0'")
    expect(e2e).toContain("NUXT_VITE_FS_STRICT: '0'")
    expect(e2e).toContain("NUXT_BUILD_DIR: '.nuxt/e2e'")
    expect(e2e).toContain('resolveE2EWebPort()')
    expect(e2e).toContain('`http://127.0.0.1:${webPort}`')
    expect(authProxy).toContain('resolveE2EWebPort()')
    expect(authProxy).toContain('`http://${hostname}:${webPort}`')
    expect(failure).toContain("NUXT_TYPECHECK: '0'")
    expect(failure).toContain("NUXT_VITE_FS_STRICT: '0'")
    expect(failure).toContain("NUXT_BUILD_DIR: '.nuxt/failure'")
    expect(e2eRunner).toContain('playwright.assistant.config.ts')
    expect(e2eRunner).toContain("!key.toUpperCase().startsWith('GAVIN_')")
    expect(e2eRunner).toContain("key.toUpperCase() === 'GAVIN_E2E_WEB_PORT'")
    const assistantWeb = read('playwright.assistant.config.ts')
    expect(assistantWeb).toContain('NUXT_PUBLIC_ASSISTANT_UI_ENABLED')
    expect(assistantWeb).toContain("NUXT_BUILD_DIR: '.nuxt/assistant'")
    expect(assistantWeb).toContain("'127.0.0.1/32,::1/128'")
    expect(assistantWeb).toContain('npm run build && npm run preview')
    expect(assistantApiRunner).toContain('assistant_session_hmac_secret=')
    expect(assistantApiRunner).toContain('assistant_csrf_hmac_secret=')
    expect(assistantApiRunner).toContain('assistant_embedding_max_batch_items=')
    expect(assistantApiRunner).toContain('assistant_embedding_provider_max_concurrency=')
    expect(assistantApiRunner).toContain('assistant_chat_provider_max_concurrency=')
    expect(assistantProxyRoute).toContain('peerAddress: getRequestIP(event)')
    expect(assistantProxyRoute).not.toContain('xForwardedFor: true')
  })

  it('accepts an alternate Web port and rejects invalid or conflicting values', () => {
    expect(resolveE2EWebPort('3110')).toBe(3110)
    expect(() => resolveE2EWebPort('not-a-port')).toThrow('integer between 1 and 65535')
    expect(() => resolveE2EWebPort('0')).toThrow('integer between 1 and 65535')
    expect(() => resolveE2EWebPort(String(E2E_API_PORT))).toThrow(
      `must differ from the API port ${E2E_API_PORT}`,
    )
  })
})
