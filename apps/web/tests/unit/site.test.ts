import { describe, expect, it } from 'vitest'

import { websiteSearchAction } from '../../utils/site'

describe('website SearchAction contract', () => {
  it('uses the same variable in the target placeholder and query-input declaration', () => {
    const action = websiteSearchAction('https://gavin.example/base')

    expect(action).toEqual({
      '@type': 'SearchAction',
      target: 'https://gavin.example/base/search?q={search_term_string}',
      'query-input': 'required name=search_term_string',
    })
    const variable = action.target.match(/\{([^}]+)\}/)?.[1]
    expect(action['query-input']).toBe(`required name=${variable}`)
    expect(new URL(action.target.replace('{search_term_string}', 'nuxt')).searchParams.get('q'))
      .toBe('nuxt')
  })
})
