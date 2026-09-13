import { describe, expect, it } from 'vitest'
import {
  articleDescription,
  extractLeadFigure,
  extractMarkdownHeadings,
  markdownToPlainText,
  normalizeStandaloneNotices,
  parseFenceInfo,
  stripMatchingTitleHeading,
} from '../../utils/markdown'

describe('extractMarkdownHeadings', () => {
  it('collects source level one and two headings at their rendered level', () => {
    expect(extractMarkdownHeadings([
      '# Body title',
      '## System Design',
      '### Failure `modes`',
      '## System Design',
    ].join('\n\n'))).toEqual([
      { level: 2, title: 'Body title', slug: 'body-title' },
      { level: 3, title: 'System Design', slug: 'system-design' },
      { level: 3, title: 'System Design', slug: 'system-design-1' },
    ])
  })

  it('keeps Chinese headings linkable', () => {
    expect(extractMarkdownHeadings('# 性能优化')).toEqual([
      { level: 2, title: '性能优化', slug: encodeURIComponent('性能优化') },
    ])
  })

  it('turns a standalone 提示 paragraph and its following paragraph into a note callout', () => {
    expect(normalizeStandaloneNotices('提示\n\n请先备份配置。\n\n## 下一步')).toBe(
      '::: note\n**提示**\n\n请先备份配置。\n:::\n\n## 下一步',
    )
  })

  it('does not rewrite 提示 when it is part of ordinary prose', () => {
    expect(normalizeStandaloneNotices('这个提示不会被转换。')).toBe('这个提示不会被转换。')
  })

  it('derives clean article descriptions from Markdown without leaking syntax', () => {
    const content = '# 接入 Codex\n\n通过 **Responses API** 使用 `deepseek-v4`。\n\n[阅读文档](https://example.com)\n\n```bash\ncodex\n```'

    expect(markdownToPlainText(content)).toBe('接入 Codex 通过 Responses API 使用 deepseek-v4。 阅读文档')
    expect(articleDescription('', content, 28)).toBe('接入 Codex 通过 Responses API 使…')
    expect(articleDescription('**明确摘要**', content)).toBe('明确摘要')
  })
})

describe('parseFenceInfo', () => {
  it('reads an optional filename after the language token', () => {
    expect(parseFenceInfo('toml config.toml')).toEqual({ language: 'toml', filename: 'config.toml' })
    expect(parseFenceInfo('ts')).toEqual({ language: 'ts', filename: null })
    expect(parseFenceInfo('js {1,3-4}')).toEqual({ language: 'js', filename: null })
  })
})

describe('stripMatchingTitleHeading', () => {
  it('removes a leading heading that repeats the page title', () => {
    expect(stripMatchingTitleHeading('# 阅读页视觉合同\n\n## 接入 Codex', '阅读页视觉合同'))
      .toBe('## 接入 Codex')
  })

  it('keeps a different opening heading', () => {
    expect(stripMatchingTitleHeading('# 另一节\n\n正文', '阅读页视觉合同')).toBe('# 另一节\n\n正文')
  })
})

describe('extractLeadFigure', () => {
  it('lifts the first block image after an optional title heading', () => {
    const extracted = extractLeadFigure('# DeepSeek 接入 Codex\n\n![请求链路](/og/gavin-notes-default.png)\n\n正文从这里开始。')
    expect(extracted).toEqual({
      src: '/og/gavin-notes-default.png',
      alt: '请求链路',
      content: '# DeepSeek 接入 Codex\n\n正文从这里开始。',
    })
  })

  it('does not lift an image that is not at the start of the body', () => {
    expect(extractLeadFigure('# 标题\n\n先读这段。\n\n![图](/og/gavin-notes-default.png)')).toBeNull()
    expect(extractLeadFigure('![bad](javascript:alert(1))')).toBeNull()
  })
})
