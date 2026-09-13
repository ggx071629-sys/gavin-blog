import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

function fixture(relativePath: string): string {
  return readFileSync(new URL(relativePath, import.meta.url), 'utf8')
}

describe('assistant development integration', () => {
  it('tracked assistant development entry is loopback-only and preserves normal defaults', () => {
    const rootPackage = JSON.parse(fixture('../../../../package.json'))
    const runner = fixture('../../../../scripts/run-assistant-dev.mjs')
    const nuxtConfig = fixture('../../nuxt.config.ts')
    const apiRunner = fixture('../../../api/scripts/run_assistant_dev.py')

    expect(rootPackage.scripts['dev:assistant']).toBe('node scripts/run-assistant-dev.mjs')
    expect(runner).toContain("const host = '127.0.0.1'")
    expect(runner).toContain("mkdtemp(join(tmpdir(), 'gavin-assistant-dev-'))")
    expect(runner).toContain("NUXT_BUILD_DIR: '.nuxt/assistant-dev'")
    expect(runner).toContain("NUXT_PUBLIC_ASSISTANT_LOCAL_DEV_MODE: real ? 'false' : 'true'")
    expect(runner).toContain('await removeRunRoot(runRoot)')
    expect(nuxtConfig).toContain("process.env.NUXT_BUILD_DIR === '.nuxt/assistant-dev'")
    expect(nuxtConfig).toContain(
      "assistantUiEnabled: process.env.NUXT_PUBLIC_ASSISTANT_UI_ENABLED === 'true'",
    )
    expect(apiRunner).toContain('if args.host not in {"127.0.0.1", "::1"}')
  })
})
