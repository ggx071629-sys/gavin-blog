import { describe, expect, it } from 'vitest'
import { insertAtRange, missingImageAltLocation, replaceMediaMarker } from '../../utils/markdown-media'

describe('markdown media helpers', () => {
  it('inserts and replaces an upload marker at the captured range', () => {
    const marker = '<!-- uploading -->'
    const value = insertAtRange('before after', marker, 7, 7)
    expect(value).toBe('before <!-- uploading -->after')
    expect(replaceMediaMarker(value, marker, '![](/image.webp)')).toBe('before ![](/image.webp)after')
  })

  it('locates the first blank image alt without flagging links or described images', () => {
    expect(missingImageAltLocation('[链接](/x)\n![图](/x)')).toBeNull()
    expect(missingImageAltLocation('标题\n\n![](/x)')).toEqual({ line: 3, column: 1 })
  })
})
