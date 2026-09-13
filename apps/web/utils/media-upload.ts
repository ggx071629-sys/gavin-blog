import type { MediaAsset } from '~/types/api'

export interface MediaUploadResult {
  file: File
  status: 'pending' | 'success' | 'error'
  asset?: MediaAsset
  message?: string
}

export async function uploadMediaFiles(
  files: File[],
  uploadOne: (file: File) => Promise<MediaAsset>,
  onResult: (result: MediaUploadResult) => Promise<void> | void,
): Promise<MediaUploadResult[]> {
  const results: MediaUploadResult[] = []
  for (const file of files) {
    await onResult({ file, status: 'pending' })
    try {
      const asset = await uploadOne(file)
      const result: MediaUploadResult = { file, status: 'success', asset }
      results.push(result)
      await onResult(result)
    }
    catch {
      const result: MediaUploadResult = {
        file,
        status: 'error',
        message: '请检查图片格式与大小。',
      }
      results.push(result)
      await onResult(result)
    }
  }
  return results
}
