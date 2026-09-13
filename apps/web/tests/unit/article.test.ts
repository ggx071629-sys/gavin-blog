import { describe, expect, it } from 'vitest'

import {
  slugify,
  validateArticleCreateFields,
} from '../../utils/article'

describe('article utilities', () => {

  it('creates URL-safe ASCII slugs', () => {
    expect(slugify(' Reliable  Agent Harness! ')).toBe('reliable-agent-harness')
  })

  it('requires an explicit English or pinyin slug when the title cannot generate one', () => {
    expect(validateArticleCreateFields({ title: '中文标题', slug: '' })).toEqual({
      title: '',
      slug: '当前标题无法自动生成 Slug，请填写英文或拼音 Slug。',
    })
  })

  it('rejects empty titles and slugs outside the API slug contract', () => {
    expect(validateArticleCreateFields({ title: '   ', slug: 'Invalid_slug' })).toEqual({
      title: '请输入文章标题。',
      slug: 'Slug 只能使用小写英文字母、数字和单个连字符，且不能以连字符开头或结尾。',
    })
    expect(validateArticleCreateFields({ title: 'Valid title', slug: 'valid-slug' })).toEqual({
      title: '',
      slug: '',
    })
  })

})
