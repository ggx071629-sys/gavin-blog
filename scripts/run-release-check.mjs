import { appendFileSync, existsSync, mkdirSync, readFileSync } from 'node:fs'
import { createHash, randomUUID } from 'node:crypto'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { performance } from 'node:perf_hooks'
import path from 'node:path'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const apiDir = path.join(root, 'apps', 'api')
const contractPath = path.join(root, 'packages', 'contracts', 'openapi.json')
const releaseStageContractPath = path.join(root, 'scripts', 'release-stage-contract.json')
const proofPrefix = 'HARNESS_RELEASE_PROOF '
const python = process.platform === 'win32'
  ? path.join(apiDir, '.venv', 'Scripts', 'python.exe')
  : path.join(apiDir, '.venv', 'bin', 'python')
const npmCli = process.env.npm_execpath
const telemetryDir = path.join(root, 'harness', 'telemetry', 'local')
const telemetryPath = path.join(telemetryDir, 'release.jsonl')
const releaseRunId = randomUUID()
const releaseStarted = performance.now()
const harnessBaseRef = process.env.HARNESS_BASE_REF
const harnessHeadRef = process.env.HARNESS_HEAD_REF || 'HEAD'
const changeCoverageMode = harnessBaseRef ? 'enforced' : 'skipped'
let stageCount = 0
let releaseFinished = false
let releaseStageContract
let releaseStageContractSha256
const completedContractStages = []

function observe(kind, value) {
  const event = {
    schema_version: 1,
    observed_at: new Date().toISOString(),
    kind,
    task_id: null,
    value,
    source: 'quality:release',
  }
  try {
    mkdirSync(telemetryDir, { recursive: true })
    appendFileSync(telemetryPath, `${JSON.stringify(event)}\n`, 'utf8')
  } catch (error) {
    console.warn(`[release] telemetry observation failed: ${error.message}`)
  }
}

function recordStage(stage, status, durationMs, exitCode) {
  stageCount += 1
  observe('release.stage', {
    run_id: releaseRunId,
    stage,
    status,
    duration_ms: Math.round(durationMs * 1000) / 1000,
    exit_code: exitCode,
    change_coverage: changeCoverageMode,
  })
}

function finishRelease(status, exitCode) {
  if (releaseFinished) return
  releaseFinished = true
  observe('release.run', {
    run_id: releaseRunId,
    status,
    duration_ms: Math.round((performance.now() - releaseStarted) * 1000) / 1000,
    exit_code: exitCode,
    stage_count: stageCount,
    change_coverage: changeCoverageMode,
  })
}

function failContract(message) {
  console.error(`[release] ${message}`)
  recordStage('stage-contract', 'failed', 0, 1)
  finishRelease('failed', 1)
  process.exit(1)
}

function loadReleaseStageContract() {
  let raw
  let payload
  try {
    raw = readFileSync(releaseStageContractPath)
    payload = JSON.parse(raw.toString('utf8'))
  } catch (error) {
    failContract(`release stage contract is unreadable: ${error.message}`)
  }
  if (
    payload?.schema_version !== 1
    || payload?.owner_gate !== 'release'
    || !Array.isArray(payload?.stages)
    || payload.stages.length === 0
  ) {
    failContract('release stage contract identity or stages are invalid')
  }
  const gates = new Set()
  const stages = new Set()
  for (const item of payload.stages) {
    if (
      !item
      || Object.keys(item).sort().join(',') !== 'command,cwd,gate,stage'
      || typeof item.gate !== 'string'
      || typeof item.stage !== 'string'
      || typeof item.cwd !== 'string'
      || !Array.isArray(item.command)
      || item.command.length === 0
      || item.command.some(value => typeof value !== 'string' || value.length === 0)
      || gates.has(item.gate)
      || stages.has(item.stage)
    ) {
      failContract('release stage contract contains an invalid or duplicate entry')
    }
    gates.add(item.gate)
    stages.add(item.stage)
  }
  releaseStageContractSha256 = createHash('sha256').update(raw).digest('hex')
  releaseStageContract = payload
}

if (!existsSync(python)) {
  console.error(`API virtual environment not found: ${python}`)
  console.error('Create apps/api/.venv and install the API dev dependencies before running the release gate.')
  recordStage('environment', 'failed', 0, 1)
  finishRelease('failed', 1)
  process.exit(1)
}

function run(stage, label, command, args, cwd) {
  console.log(`\n[release] ${label}`)
  const started = performance.now()
  const result = spawnSync(command, args, {
    cwd,
    env: { ...process.env, CI: '1' },
    stdio: 'inherit',
  })
  if (result.error) {
    recordStage(stage, 'failed', performance.now() - started, null)
    console.error(result.error.message)
    finishRelease('failed', 1)
    process.exit(1)
  }
  recordStage(
    stage,
    result.status === 0 ? 'passed' : 'failed',
    performance.now() - started,
    result.status,
  )
  if (result.status !== 0) {
    finishRelease('failed', result.status ?? 1)
    process.exit(result.status ?? 1)
  }
}

function runContractGate(gate, label) {
  const item = releaseStageContract.stages.find(candidate => candidate.gate === gate)
  if (!item || completedContractStages.some(candidate => candidate.gate === gate)) {
    failContract(`contract gate ${gate} is missing or was executed more than once`)
  }
  const cwd = path.resolve(root, item.cwd)
  if (cwd !== root && !cwd.startsWith(`${root}${path.sep}`)) {
    failContract(`contract gate ${gate} cwd escapes the project`)
  }
  const [executable, ...args] = item.command
  if (executable === '{api_python}') {
    run(item.stage, label, python, args, cwd)
  } else if (executable === 'npm') {
    if (!npmCli || !existsSync(npmCli)) {
      failContract('npm CLI path is unavailable; run release through npm')
    }
    run(item.stage, label, process.execPath, [npmCli, ...args], cwd)
  } else {
    failContract(`contract gate ${gate} uses an unsupported executable`)
  }
  completedContractStages.push({ gate: item.gate, stage: item.stage })
}

function emitSubsumptionProof() {
  const expected = releaseStageContract.stages.map(item => ({
    gate: item.gate,
    stage: item.stage,
  }))
  if (JSON.stringify(completedContractStages) !== JSON.stringify(expected)) {
    failContract('not every release stage contract entry completed exactly once')
  }
  console.log(`${proofPrefix}${JSON.stringify({
    schema_version: 1,
    owner_gate: 'release',
    contract_sha256: releaseStageContractSha256,
    completed: completedContractStages,
  })}`)
}

loadReleaseStageContract()

if (harnessBaseRef) {
  run(
    'harness-change-coverage',
    'Harness change coverage',
    python,
    ['-m', 'tools.harness', 'change-check', '--base', harnessBaseRef, '--head', harnessHeadRef],
    path.join(root, 'harness'),
  )
} else {
  console.log('\n[release] Harness change coverage skipped: HARNESS_BASE_REF is not set (local-only mode).')
  recordStage('harness-change-coverage', 'skipped', 0, null)
}

runContractGate('api-lint', 'API lint')
runContractGate('api-typecheck', 'API typecheck')
runContractGate('api-tests', 'API tests')
runContractGate('harness-tests', 'Harness check tests')

const contractBefore = readFileSync(contractPath, 'utf8')
const contractTypesPath = path.join(root, 'packages', 'contracts', 'api-types.d.ts')
const contractTypesBefore = readFileSync(contractTypesPath, 'utf8')
if (!npmCli || !existsSync(npmCli)) {
  failContract('npm CLI path is unavailable; run release through npm')
}
run(
  'openapi-export',
  'OpenAPI snapshot and derived TypeScript types',
  process.execPath,
  [npmCli, '--workspace', '@gavin/contracts', 'run', 'generate'],
  root,
)
const contractAfter = readFileSync(contractPath, 'utf8')
const contractTypesAfter = readFileSync(contractTypesPath, 'utf8')
if (contractAfter !== contractBefore || contractTypesAfter !== contractTypesBefore) {
  recordStage('openapi-consistency', 'failed', 0, 1)
  console.error(
    '\n[release] Contract artifacts were stale and have been regenerated. Review and commit packages/contracts/openapi.json and packages/contracts/api-types.d.ts, then rerun the gate.',
  )
  finishRelease('failed', 1)
  process.exit(1)
}
recordStage('openapi-consistency', 'passed', 0, 0)

runContractGate('web-quality', 'Web quality gate')
runContractGate('e2e', 'Core E2E journeys')
runContractGate('harness-integrity', 'Harness integrity')

emitSubsumptionProof()
finishRelease('passed', 0)
console.log('\n[release] Local release candidate checks passed.')
