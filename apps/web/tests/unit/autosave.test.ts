import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  AutosaveQueue,
  flushAutosaveBeforeNavigation,
  preventUnloadWhenAutosaveIsDirty,
  type AutosaveState,
} from '../../utils/autosave'

afterEach(() => vi.useRealTimers())

describe('AutosaveQueue', () => {
  it('debounces edits and saves only the latest snapshot', async () => {
    vi.useFakeTimers()
    const saved: string[] = []
    const states: AutosaveState[] = []
    const queue = new AutosaveQueue<string>(
      async value => { saved.push(value) },
      state => { states.push(state) },
      100,
    )
    queue.schedule('first')
    queue.schedule('latest')
    await vi.advanceTimersByTimeAsync(100)
    expect(saved).toEqual(['latest'])
    expect(states.at(-1)).toBe('saved')
  })

  it('reports optimistic locking conflicts', async () => {
    const states: AutosaveState[] = []
    const conflict = { statusCode: 409, data: { detail: 'article was updated elsewhere' } }
    const queue = new AutosaveQueue<string>(
      async () => { throw conflict },
      state => { states.push(state) },
      0,
    )
    queue.schedule('change')
    await expect(queue.flush()).rejects.toBe(conflict)
    expect(states.at(-1)).toBe('conflict')
  })

  it('treats published-slug 409 as a save error instead of a version conflict', async () => {
    const states: AutosaveState[] = []
    const locked = { statusCode: 409, data: { detail: 'published article slug cannot be changed' } }
    const queue = new AutosaveQueue<string>(
      async () => { throw locked },
      state => { states.push(state) },
      0,
    )
    queue.schedule('change')
    await expect(queue.flush()).rejects.toBe(locked)
    expect(states.at(-1)).toBe('error')
  })

  it('waits for an in-flight save and drains the latest queued snapshot', async () => {
    let releaseFirst: (() => void) | undefined
    const firstSave = new Promise<void>((resolve) => { releaseFirst = resolve })
    const saved: string[] = []
    const queue = new AutosaveQueue<string>(
      async (value) => {
        saved.push(value)
        if (value === 'first') await firstSave
      },
      () => undefined,
      1_000,
    )

    queue.schedule('first')
    const initialFlush = queue.flush()
    queue.schedule('latest')
    let barrierResolved = false
    const publishBarrier = queue.flush().then(() => { barrierResolved = true })
    await Promise.resolve()
    expect(barrierResolved).toBe(false)

    releaseFirst?.()
    await Promise.all([initialFlush, publishBarrier])
    expect(saved).toEqual(['first', 'latest'])
  })

  it('retains a failed snapshot for an explicit retry', async () => {
    const failure = new Error('network unavailable')
    let shouldFail = true
    const attempts: string[] = []
    const queue = new AutosaveQueue<string>(
      async (value) => {
        attempts.push(value)
        if (shouldFail) throw failure
      },
      () => undefined,
      1_000,
    )

    queue.schedule('draft')
    await expect(queue.flush()).rejects.toBe(failure)
    shouldFail = false
    await queue.flush()
    expect(attempts).toEqual(['draft', 'draft'])
  })

  it.each([0, 300, 899])(
    'flushes the latest snapshot before navigation at %dms',
    async (elapsed) => {
      vi.useFakeTimers()
      const saved: string[] = []
      const queue = new AutosaveQueue<string>(
        async value => { saved.push(value) },
        () => undefined,
        900,
      )

      queue.schedule(`draft-${elapsed}`)
      await vi.advanceTimersByTimeAsync(elapsed)

      await expect(flushAutosaveBeforeNavigation(queue)).resolves.toBe(true)
      expect(saved).toEqual([`draft-${elapsed}`])
      expect(queue.isDirty).toBe(false)
    },
  )

  it('blocks navigation and retains the snapshot when flush fails', async () => {
    const failure = new Error('request timed out')
    const onError = vi.fn()
    const queue = new AutosaveQueue<string>(
      async () => { throw failure },
      () => undefined,
      900,
    )

    queue.schedule('local content')

    await expect(flushAutosaveBeforeNavigation(queue, onError)).resolves.toBe(false)
    expect(onError).toHaveBeenCalledWith(failure)
    expect(queue.isDirty).toBe(true)
  })

  it('prompts before unload only while a snapshot is dirty', async () => {
    vi.useFakeTimers()
    const queue = new AutosaveQueue<string>(async () => undefined, () => undefined, 900)
    const cleanEvent = { preventDefault: vi.fn(), returnValue: undefined }
    preventUnloadWhenAutosaveIsDirty(cleanEvent as unknown as BeforeUnloadEvent, queue)
    expect(cleanEvent.preventDefault).not.toHaveBeenCalled()

    queue.schedule('dirty')
    const dirtyEvent = { preventDefault: vi.fn(), returnValue: undefined }
    preventUnloadWhenAutosaveIsDirty(dirtyEvent as unknown as BeforeUnloadEvent, queue)
    expect(dirtyEvent.preventDefault).toHaveBeenCalledOnce()
    expect(dirtyEvent.returnValue).toBe('')

    await queue.dispose()
    expect(queue.isDirty).toBe(false)
  })
})
