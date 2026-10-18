import { describe, expect, it } from 'vitest'
import { applyWikilinks } from '../../utils/wikilinks'

describe('applyWikilinks', () => {
  it('turns resolved tokens into markdown links and leaves code alone', () => {
    const content = [
      'See [[alpha]] and [[project:gavin|案例]].',
      '',
      '```md',
      '[[ignored]]',
      '```',
      '',
      'Inline `[[also]]` stays.',
    ].join('\n')
    expect(applyWikilinks(content, [
      { token: 'alpha', display_title: 'alpha', public_path: '/notes/2026/08/alpha', content_type: 'article' },
      { token: 'project:gavin', display_title: '案例', public_path: '/projects/gavin', content_type: 'project' },
    ])).toContain('[alpha](/notes/2026/08/alpha)')
    expect(applyWikilinks(content, [
      { token: 'alpha', display_title: 'alpha', public_path: '/notes/2026/08/alpha', content_type: 'article' },
      { token: 'project:gavin', display_title: '案例', public_path: '/projects/gavin', content_type: 'project' },
    ])).toContain('[案例](/projects/gavin)')
    expect(applyWikilinks(content, [])).toContain('[[ignored]]')
    expect(applyWikilinks(content, [])).toContain('`[[also]]`')
  })

  it('renders unresolved tokens as plain text', () => {
    expect(applyWikilinks('See [[missing]]', [])).toBe('See missing')
  })
})
