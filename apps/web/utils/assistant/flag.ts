export function isAssistantUiEnabled(raw: unknown): boolean {
  return raw === true || raw === 'true'
}
