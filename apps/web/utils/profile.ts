export const PROFILE_MAX_SKILLS = 6
export const PROFILE_SKILL_MAX_LENGTH = 30

export function isValidSkill(value: string): boolean {
  const trimmed = value.trim()
  return trimmed.length >= 1 && trimmed.length <= PROFILE_SKILL_MAX_LENGTH
}

export function canAddSkill(skills: string[], value: string): boolean {
  return skills.length < PROFILE_MAX_SKILLS && isValidSkill(value)
}

export function reorderSkills(skills: string[], from: number, to: number): string[] {
  if (from < 0 || from >= skills.length || to < 0 || to >= skills.length) return skills
  const next = [...skills]
  const [moved] = next.splice(from, 1)
  if (moved === undefined) return skills
  next.splice(to, 0, moved)
  return next
}
