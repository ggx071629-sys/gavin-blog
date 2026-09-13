import { randomBytes } from 'node:crypto'
import { existsSync } from 'node:fs'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { spawn, spawnSync } from 'node:child_process'
import { stopTree } from './assistant-dev-process.mjs'
import { createServer } from 'node:net'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const apiDir = join(root, 'apps', 'api')
const apiPython = process.platform === 'win32'
  ? join(apiDir, '.venv', 'Scripts', 'python.exe')
  : join(apiDir, '.venv', 'bin', 'python')
const npmCli = process.env.npm_execpath
const host = '127.0.0.1'
const real = process.argv.includes('--real')

function port(name, fallback) {
  const value = Number(process.env[name] || fallback)
  if (!Number.isInteger(value) || value < 1 || value > 65_535) {
    throw new Error(`${name} must be an integer between 1 and 65535`)
  }
  return value
}

function assertPortAvailable(value) {
  return new Promise((resolvePromise, reject) => {
    const server = createServer()
    server.unref()
    server.once('error', () => reject(new Error(`loopback port ${value} is already in use`)))
    server.listen(value, host, () => server.close(resolvePromise))
  })
}

function waitFor(url, child, timeoutMs = 120_000) {
  const started = Date.now()
  return new Promise((resolvePromise, reject) => {
    let timer
    const onExit = (code) => {
      clearTimeout(timer)
      reject(new Error(`process exited before ${url} became ready (code ${code ?? 1})`))
    }
    child.once('exit', onExit)
    const probe = async () => {
      try {
        const response = await fetch(url, { redirect: 'error', signal: AbortSignal.timeout(2_000) })
        if (response.ok) {
          child.off('exit', onExit)
          resolvePromise()
          return
        }
      }
      catch {
        // The child is still starting.
      }
      if (Date.now() - started >= timeoutMs) {
        child.off('exit', onExit)
        reject(new Error(`timed out waiting for ${url}`))
        return
      }
      timer = setTimeout(probe, 250)
    }
    void probe()
  })
}
async function removeRunRoot(runRoot) {
  let lastError
  for (let attempt = 0; attempt < 120; attempt += 1) {
    try {
      await rm(runRoot, { recursive: true, force: true })
      return
    }
    catch (error) {
      lastError = error
      await new Promise(resolvePromise => setTimeout(resolvePromise, 250))
    }
  }
  throw lastError
}

const webPort = port('GAVIN_ASSISTANT_DEV_WEB_PORT', 3101)
const apiPort = port('GAVIN_ASSISTANT_DEV_API_PORT', 8101)
if (webPort === apiPort) throw new Error('assistant development Web and API ports must differ')
if (!existsSync(apiPython)) {
  throw new Error(`API virtual environment not found: ${apiPython}`)
}
if (!npmCli || !existsSync(npmCli)) {
  throw new Error('npm CLI path is unavailable; run this command through npm')
}

await Promise.all([assertPortAvailable(webPort), assertPortAvailable(apiPort)])

const runRoot = real ? join(apiDir, 'data', 'assistant-local-real') : await mkdtemp(join(tmpdir(), 'gavin-assistant-dev-'))
function realProxySecret() {
  const result = spawnSync(apiPython, ['-c', 'from app.config import Settings; print(Settings().assistant_proxy_hmac_secret or "")'], { cwd: apiDir, encoding: 'utf8', windowsHide: true })
  if (result.status !== 0 || result.stdout.trim().length < 32) throw new Error('Configure a persistent assistant proxy HMAC secret in apps/api/.env')
  return result.stdout.trim()
}
const proxySecret = real ? realProxySecret() : randomBytes(32).toString('hex')
const webOrigin = `http://${host}:${webPort}`
const apiOrigin = `http://${host}:${apiPort}`
const children = []
let shutdownPromise
let requestedExit = false
let rejectChildFailure
const childFailure = new Promise((_, reject) => { rejectChildFailure = reject })
// Each race below observes this promise, including failures during startup.
childFailure.catch(() => {})

function supervise(child) {
  children.push(child)
  child.stdout?.pipe(process.stdout, { end: false })
  child.stderr?.pipe(process.stderr, { end: false })
  child.once('error', error => rejectChildFailure(error))
  child.once('exit', (code) => {
    if (!requestedExit) rejectChildFailure(new Error(`assistant development child exited (code ${code ?? 1})`))
  })
}

function shutdown() {
  shutdownPromise ??= (async () => {
    const results = await Promise.allSettled([...children].reverse().map(stopTree))
    if (!real) await removeRunRoot(runRoot)
    const failed = results.find(result => result.status === 'rejected')
    if (failed) throw failed.reason
  })()
  return shutdownPromise
}

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.once(signal, () => {
    requestedExit = true
    void shutdown().then(() => process.exit(0), (error) => {
      console.error(error)
      process.exit(1)
    })
  })
}

try {
  const api = spawn(
    apiPython,
    ['scripts/run_assistant_dev.py', '--host', host, '--port', String(apiPort), '--web-origin', webOrigin, ...(real ? ['--real'] : [])],
    {
      cwd: apiDir,
      env: {
        ...process.env,
        GAVIN_ASSISTANT_DEV_RUN_ROOT: runRoot,
        GAVIN_ASSISTANT_DEV_PROXY_SECRET: proxySecret,
        LANGSMITH_TRACING: 'false',
        LANGCHAIN_TRACING_V2: 'false',
      },
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
      detached: true,
    },
  )
  supervise(api)
  await Promise.race([waitFor(`${apiOrigin}/api/health`, api), childFailure])

  const web = spawn(
    process.execPath,
    [npmCli, '--workspace', '@gavin/web', 'run', 'dev', '--', '--host', host, '--port', String(webPort)],
    {
      cwd: root,
      env: {
        ...process.env,
        NUXT_PUBLIC_API_BASE: '/api/v1',
        NUXT_API_UPSTREAM: apiOrigin,
        NUXT_PUBLIC_SITE_URL: webOrigin,
        NUXT_PUBLIC_ASSISTANT_UI_ENABLED: 'true',
        NUXT_PUBLIC_ASSISTANT_LOCAL_DEV_MODE: real ? 'false' : 'true',
        NUXT_ASSISTANT_TRUSTED_EDGE_PROXIES: '127.0.0.1/32,::1/128',
        NUXT_ASSISTANT_EDGE_CLIENT_IP_HEADER: 'X-Gavin-Edge-Client-IP',
        NUXT_ASSISTANT_API_CLIENT_IP_HEADER: 'X-Gavin-Client-IP',
        NUXT_ASSISTANT_PROXY_HMAC_SECRET: proxySecret,
        NUXT_ASSISTANT_DEV_DIRECT_LOOPBACK: 'true',
        NUXT_BUILD_DIR: '.nuxt/assistant-dev',
        NUXT_IGNORE_LOCK: '1',
        NUXT_TELEMETRY_DISABLED: '1',
      },
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
      detached: true,
    },
  )
  supervise(web)
  await Promise.race([waitFor(webOrigin, web), childFailure])
  console.log(`\n[assistant-dev] ready: ${webOrigin}`)
  console.log(real ? '[assistant-dev] real E5 + Chat; persistent local budget' : '[assistant-dev] offline evidence adapter; production remains disabled')

  await childFailure
}
finally {
  await shutdown()
}
