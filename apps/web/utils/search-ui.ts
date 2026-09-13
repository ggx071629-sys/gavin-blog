export type SearchUiState = 'idle' | 'loading' | 'results' | 'empty'

export function searchUiState(input: {
  query: string
  pending: boolean
  itemCount: number
}): SearchUiState {
  if (!input.query) return 'idle'
  if (input.pending) return 'loading'
  return input.itemCount > 0 ? 'results' : 'empty'
}
