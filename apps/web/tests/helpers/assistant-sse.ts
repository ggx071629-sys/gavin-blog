export function splitSseForTest(text: string, sizes: number[]): Uint8Array[] {
  const bytes = new TextEncoder().encode(text)
  const chunks: Uint8Array[] = []
  let offset = 0
  let index = 0
  while (offset < bytes.length) {
    const size = sizes[index % sizes.length] ?? bytes.length
    chunks.push(bytes.slice(offset, offset + size))
    offset += size
    index += 1
  }
  return chunks
}
