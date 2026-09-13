export function readingMinutesFromContent(content: string): number {
  return Math.max(1, Math.ceil(content.length / 500))
}
