type QueryValue = string | number | null | undefined
type RouteQueryValue = string | (string | null)[] | null | undefined

export const MAX_PAGE_OFFSET = 100_000

function requirePageSize(pageSize: number): void {
  if (!Number.isSafeInteger(pageSize) || pageSize < 1) {
    throw new RangeError('pageSize must be a positive integer')
  }
}

export function maxPageFor(pageSize: number, maxOffset = MAX_PAGE_OFFSET): number {
  requirePageSize(pageSize)
  if (!Number.isSafeInteger(maxOffset) || maxOffset < 0) {
    throw new RangeError('maxOffset must be a non-negative integer')
  }
  return Math.floor(maxOffset / pageSize) + 1
}

export function pageFromQuery(value: RouteQueryValue, pageSize: number): number {
  const candidate = Array.isArray(value) ? value[0] : value
  const page = Number(candidate)
  if (!Number.isSafeInteger(page) || page < 1) return 1
  return Math.min(page, maxPageFor(pageSize))
}

export function canonicalPageQuery(value: RouteQueryValue, pageSize: number): string | undefined {
  const page = pageFromQuery(value, pageSize)
  return page > 1 ? String(page) : undefined
}

export function boundedPageOffset(page: number, pageSize: number): number {
  return (pageFromQuery(String(page), pageSize) - 1) * pageSize
}

export function paginatedApiPath(
  path: string,
  page: number,
  pageSize: number,
  query: Record<string, QueryValue> = {},
): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== null && value !== undefined && value !== '') params.set(key, String(value))
  }
  params.set('limit', String(pageSize + 1))
  params.set('offset', String(boundedPageOffset(page, pageSize)))
  return `${path}?${params.toString()}`
}

export function paginationWindow<T>(values: T[] | null | undefined, pageSize: number) {
  const source = values || []
  return {
    items: source.slice(0, pageSize),
    hasNext: source.length > pageSize,
  }
}

export function pageLink(
  path: string,
  page: number,
  query: Record<string, QueryValue> = {},
) {
  const nextQuery: Record<string, string> = {}
  for (const [key, value] of Object.entries(query)) {
    if (value !== null && value !== undefined && value !== '') nextQuery[key] = String(value)
  }
  if (page > 1) nextQuery.page = String(page)
  return { path, query: nextQuery }
}

export async function fetchAllPages<T>(
  request: (limit: number, offset: number) => Promise<T[]>,
  batchSize = 100,
): Promise<T[]> {
  if (!Number.isInteger(batchSize) || batchSize < 1 || batchSize > 100) {
    throw new RangeError('batchSize must be between 1 and 100')
  }
  const items: T[] = []
  for (let offset = 0; offset <= MAX_PAGE_OFFSET; offset += batchSize) {
    const batch = await request(batchSize, offset)
    items.push(...batch)
    if (batch.length < batchSize) return items
  }
  throw new RangeError('complete collection exceeds the supported pagination window')
}
