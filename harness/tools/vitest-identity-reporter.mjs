// Public Vitest reporter API; no private task IDs are used as stable identities.
import { writeFileSync } from 'node:fs'

export default class IdentityReporter {
  started = new Set()
  rows = []

  onTestCaseReady(test) {
    this.started.add(test.id)
  }

  onTestCaseResult(test) {
    if (!this.started.has(test.id)) return
    const titles = [test.name]
    for (let parent = test.parent; parent?.type === 'suite'; parent = parent.parent) {
      titles.unshift(parent.name)
    }
    const diagnostic = test.diagnostic()
    const result = test.result()
    this.rows.push({
      kind: 'vitest', config: 'vitest.config.ts', project: test.project.name,
      path: test.module.moduleId, title_path: titles,
      status: result.state, retry_count: diagnostic?.retryCount,
      repeat_count: diagnostic?.repeatCount, errors: result.errors?.length || 0,
    })
  }

  onTestRunEnd(_modules, errors) {
    writeFileSync(process.env.HARNESS_VITEST_REPORT, JSON.stringify({
      version: 3, rows: this.rows, errors: errors.length,
    }))
  }
}
