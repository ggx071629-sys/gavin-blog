import { describe, expect, it } from 'vitest'
import { isAbortError } from '../../utils/api-errors'
import { searchUiState } from '../../utils/search-ui'

describe('search UI state', () => {
  it('maps query, pending, and item count onto a single exclusive state', () => {
    expect(searchUiState({ query: '', pending: false, itemCount: 0 })).toBe('idle')
    expect(searchUiState({ query: '', pending: true, itemCount: 3 })).toBe('idle')
    expect(searchUiState({ query: 'nuxt', pending: true, itemCount: 3 })).toBe('loading')
    expect(searchUiState({ query: 'nuxt', pending: false, itemCount: 2 })).toBe('results')
    expect(searchUiState({ query: 'nuxt', pending: false, itemCount: 0 })).toBe('empty')
  })

  it('does not treat abort as an API classification error', () => {
    expect(isAbortError(new DOMException('cancelled', 'AbortError'))).toBe(true)
    expect(isAbortError({ name: 'AbortError', cause: undefined })).toBe(true)
    expect(isAbortError({ name: 'FetchError', cause: { name: 'AbortError' } })).toBe(true)
    expect(isAbortError({ statusCode: 503 })).toBe(false)
  })
})
