export const insertAtRange = (value: string, insertion: string, start: number, end = start) =>
  `${value.slice(0, start)}${insertion}${value.slice(end)}`

export const replaceMediaMarker = (value: string, marker: string, replacement: string) =>
  value.includes(marker) ? value.replace(marker, replacement) : value

export const missingImageAltLocation = (markdown: string) => {
  const image = /!\[([^\]]*)\]\(/g
  for (const match of markdown.matchAll(image)) {
    if (match[1]?.trim()) continue
    const index = match.index ?? 0
    const before = markdown.slice(0, index)
    return {
      line: before.split('\n').length,
      column: index - before.lastIndexOf('\n'),
    }
  }
  return null
}
