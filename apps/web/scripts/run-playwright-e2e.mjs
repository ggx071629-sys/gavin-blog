import { randomUUID } from 'node:crypto'
import { mkdir, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'
import { createRequire } from 'node:module'
import { spawn } from 'node:child_process'

const require = createRequire(import.meta.url)
const playwrightCli = join(dirname(require.resolve('playwright')), 'cli.js')
const runRoot = join(tmpdir(), `gavin-e2e-${randomUUID()}`)
const inheritedEnv = Object.fromEntries(
  Object.entries(process.env).filter(([key]) => (
    !key.toUpperCase().startsWith('GAVIN_')
    || key.toUpperCase() === 'GAVIN_E2E_WEB_PORT'
  )),
)
const e2eEnv = { ...inheritedEnv, GAVIN_E2E_RUN_ROOT: runRoot }

await mkdir(runRoot, { recursive: false })

const run = args => new Promise((resolve, reject) => {
  const child = spawn(process.execPath, [playwrightCli, 'test', ...args], {
    env: e2eEnv,
    stdio: 'inherit',
  })
  child.once('error', reject)
  child.once('exit', code => resolve(code ?? 1))
})

let exitCode
try {
  exitCode = await run(process.argv.slice(2))
  if (exitCode === 0) {
    exitCode = await run(['--config', 'playwright.assistant.config.ts'])
  }
}
finally {
  await rm(runRoot, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 })
}

process.exitCode = exitCode
