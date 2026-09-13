import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

describe('assistant source titles', () => {
  it('shows source titles while retaining navigation targets without path labels', () => {
    const panel = readFileSync(resolve(process.cwd(), 'components/AssistantPanel.vue'), 'utf8')
    const sourceLink = panel.match(/<NuxtLink v-else :to="source.path"[\s\S]*?<\/NuxtLink>/)?.[0]
    expect(sourceLink).toBeDefined()
    expect(sourceLink).toContain('{{ source.title }}')
    expect(sourceLink).not.toContain('{{ source.path }}')
    expect(sourceLink).toContain(':to="source.path"')
    expect(sourceLink).toContain("$emit('source', source.path)")
  })
})
