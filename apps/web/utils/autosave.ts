import { isOptimisticLockConflict } from './api-errors'

export type AutosaveState = 'idle' | 'pending' | 'saving' | 'saved' | 'error' | 'conflict'

export class AutosaveQueue<T> {
  private timer: ReturnType<typeof setTimeout> | undefined
  private latest: T | undefined
  private active: Promise<void> | undefined
  private lastError: unknown | undefined

  constructor(
    private readonly save: (value: T) => Promise<void>,
    private readonly onState: (state: AutosaveState) => void,
    private readonly delay = 900,
  ) {}

  get isDirty(): boolean {
    return this.timer !== undefined || this.latest !== undefined || this.active !== undefined
  }

  schedule(value: T): void {
    this.latest = value
    this.lastError = undefined
    this.onState('pending')
    if (this.timer) clearTimeout(this.timer)
    this.timer = setTimeout(() => {
      void this.flush().catch(() => undefined)
    }, this.delay)
  }

  async flush(): Promise<void> {
    if (this.timer) clearTimeout(this.timer)
    this.timer = undefined

    if (!this.active && this.latest !== undefined) {
      this.active = this.drain()
      try {
        await this.active
      }
      finally {
        this.active = undefined
      }
    }
    else if (this.active) {
      await this.active
    }

    if (this.lastError !== undefined) throw this.lastError
    if (this.latest !== undefined) await this.flush()
  }

  private async drain(): Promise<void> {
    while (this.latest !== undefined) {
      const value = this.latest
      this.latest = undefined
      this.onState('saving')
      try {
        await this.save(value)
        this.lastError = undefined
        this.onState('saved')
      }
      catch (error: unknown) {
        if (this.latest === undefined) this.latest = value
        this.lastError = error
        this.onState(isOptimisticLockConflict(error) ? 'conflict' : 'error')
        return
      }
    }
  }

  async dispose(): Promise<void> {
    await this.flush()
  }
}

export async function flushAutosaveBeforeNavigation<T>(
  queue: AutosaveQueue<T>,
  onError?: (error: unknown) => void,
): Promise<boolean> {
  try {
    await queue.flush()
    return true
  }
  catch (error) {
    onError?.(error)
    return false
  }
}

export function preventUnloadWhenAutosaveIsDirty<T>(
  event: BeforeUnloadEvent,
  queue: AutosaveQueue<T>,
): void {
  if (!queue.isDirty) return
  event.preventDefault()
  event.returnValue = ''
}
