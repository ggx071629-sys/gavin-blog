import { describe, expect, it } from 'vitest'
import {
  PROFILE_MAX_SKILLS,
  PROFILE_SKILL_MAX_LENGTH,
  canAddSkill,
  isValidSkill,
  reorderSkills,
} from '../../utils/profile'

describe('isValidSkill', () => {
  it('accepts trimmed skills within the length bound', () => {
    expect(isValidSkill('FastAPI')).toBe(true)
    expect(isValidSkill('  Nuxt  ')).toBe(true)
    expect(isValidSkill('x'.repeat(PROFILE_SKILL_MAX_LENGTH))).toBe(true)
  })

  it('rejects empty, blank, and over-length values', () => {
    expect(isValidSkill('')).toBe(false)
    expect(isValidSkill('   ')).toBe(false)
    expect(isValidSkill('x'.repeat(PROFILE_SKILL_MAX_LENGTH + 1))).toBe(false)
  })
})

describe('canAddSkill', () => {
  it('respects the maximum skill count', () => {
    const full = Array.from({ length: PROFILE_MAX_SKILLS }, (_, index) => `skill-${index}`)
    expect(canAddSkill(full, 'Extra')).toBe(false)
    expect(canAddSkill(full.slice(0, 1), 'Extra')).toBe(true)
  })

  it('rejects invalid values even when below the cap', () => {
    expect(canAddSkill([], '')).toBe(false)
  })
})

describe('reorderSkills', () => {
  it('moves a skill to the target position without mutating the input', () => {
    const input = ['A', 'B', 'C']
    expect(reorderSkills(input, 0, 2)).toEqual(['B', 'C', 'A'])
    expect(reorderSkills(input, 2, 0)).toEqual(['C', 'A', 'B'])
    expect(input).toEqual(['A', 'B', 'C'])
  })

  it('ignores out-of-range indices and returns the input order', () => {
    expect(reorderSkills(['A', 'B'], 0, 5)).toEqual(['A', 'B'])
    expect(reorderSkills(['A', 'B'], -1, 1)).toEqual(['A', 'B'])
  })
})
