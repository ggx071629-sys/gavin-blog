import { spawnSync } from 'node:child_process'

export async function stopTree(child) {
  if (!child?.pid) return
  const exited = () => child.exitCode !== null || child.signalCode !== null
  if (exited()) return
  const waitForExit = timeoutMs => new Promise((resolvePromise) => {
    if (exited()) {
      resolvePromise()
      return
    }
    const timer = setTimeout(resolvePromise, timeoutMs)
    timer.unref()
    child.once('exit', () => {
      clearTimeout(timer)
      resolvePromise()
    })
  })
  if (process.platform === 'win32') {
    // Kill the tree while its parent still exists; killing npm first orphans Nuxt.
    const result = spawnSync('taskkill', ['/PID', String(child.pid), '/T', '/F'], {
      encoding: 'utf8', windowsHide: true, timeout: 10_000,
    })
    if (result.error) throw result.error
    if (result.status !== 0) {
      // Ctrl+C can finish a console child before taskkill observes it.
      try { process.kill(child.pid, 0) }
      catch (error) {
        if (error.code === 'ESRCH') return
        throw error
      }
      throw new Error(`assistant process tree cleanup failed: ${result.stderr}`)
    }
  }
  else {
    try {
      process.kill(-child.pid, 'SIGTERM')
    }
    catch {
      child.kill('SIGTERM')
    }
  }
  await waitForExit(5_000)
  if (!exited()) {
    if (process.platform !== 'win32') process.kill(-child.pid, 'SIGKILL')
    await waitForExit(5_000)
  }
  if (!exited()) throw new Error('assistant development child failed to stop')
}
