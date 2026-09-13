import { existsSync } from 'node:fs'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const contractsDir = path.dirname(fileURLToPath(import.meta.url))
const apiDir = path.resolve(contractsDir, '../../apps/api')
const rootDir = path.resolve(contractsDir, '../..')
const npmCli = process.env.npm_execpath
const python = process.platform === 'win32'
  ? path.join(apiDir, '.venv', 'Scripts', 'python.exe')
  : path.join(apiDir, '.venv', 'bin', 'python')

if (!existsSync(python)) {
  console.error(`API virtual environment not found: ${python}`)
  process.exit(1)
}

const result = spawnSync(python, ['-m', 'scripts.export_openapi'], {
  cwd: apiDir,
  stdio: 'inherit',
})

if (result.error) {
  console.error(result.error.message)
  process.exit(1)
}

if (result.status !== 0) {
  process.exit(result.status ?? 1)
}

if (!npmCli) {
  console.error('[contracts] openapi-typescript requires npm; run generate through npm')
  process.exit(1)
}

const types = spawnSync(process.execPath, [
  npmCli,
  'exec',
  '--workspace',
  '@gavin/contracts',
  '--',
  'openapi-typescript',
  path.join(contractsDir, 'openapi.json'),
  '-o',
  path.join(contractsDir, 'api-types.d.ts'),
], { cwd: rootDir, stdio: 'inherit' })

if (types.error) {
  console.error(types.error.message)
  process.exit(1)
}

process.exit(types.status ?? 1)
