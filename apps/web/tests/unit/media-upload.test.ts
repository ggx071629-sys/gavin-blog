import { describe, expect, it, vi } from 'vitest'

import type { MediaAsset } from '../../types/api'
import { uploadMediaFiles } from '../../utils/media-upload'

const asset = (id: number): MediaAsset => ({
  id,
  source: 'upload',
  original_name: `file-${id}.png`,
  alt_text: '',
  mime_type: 'image/webp',
  width: 1,
  height: 1,
  byte_size: 1,
  url: `/media/${id}`,
  variants: [],
  created_at: '2026-08-10T00:00:00Z',
  deleted_at: null,
})

describe('uploadMediaFiles', () => {
  it('reports success, failure, success independently and retries only failures', async () => {
    const files = ['one.png', 'two.png', 'three.png'].map(name => new File(['x'], name))
    const uploadOne = vi.fn(async (file: File) => {
      if (file.name === 'two.png') throw new Error('injected failure')
      return asset(file.name === 'one.png' ? 1 : 3)
    })
    const updates: string[] = []

    const results = await uploadMediaFiles(files, uploadOne, result => {
      updates.push(`${result.file.name}:${result.status}`)
    })

    expect(results.map(result => result.status)).toEqual(['success', 'error', 'success'])
    expect(updates).toContain('one.png:success')
    expect(updates).toContain('two.png:error')
    expect(updates).toContain('three.png:success')

    uploadOne.mockResolvedValueOnce(asset(2))
    const retried = await uploadMediaFiles(
      results.filter(result => result.status === 'error').map(result => result.file),
      uploadOne,
      () => undefined,
    )
    expect(retried.map(result => result.file.name)).toEqual(['two.png'])
    expect(retried[0]?.status).toBe('success')
  })
})
