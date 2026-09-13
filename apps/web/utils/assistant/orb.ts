export type OrbPosition = { side: 'left' | 'right', ratio: number }
export const ORB_SIZE = 52
export const ORB_POSITION_KEY = 'gavin:assistant-orb-position:v1'
export const ORB_GUIDANCE_KEY = 'gavin:assistant-orb-guidance:v1'
export const clamp = (value: number, max: number) => Math.max(0, Math.min(value, Math.max(0, max)))
export function parseOrbPosition(raw: string | null): OrbPosition {
  try {
    const value = JSON.parse(raw || 'null')
    if ((value?.side === 'left' || value?.side === 'right') && typeof value.ratio === 'number' && Number.isFinite(value.ratio)) {
      return { side: value.side, ratio: clamp(value.ratio, 1) }
    }
  }
  catch { /* Invalid preferences return to the visible default. */ }
  return { side: 'right', ratio: 1 }
}
export function orbPoint(position: OrbPosition, width: number, height: number) {
  return { x: position.side === 'left' ? 0 : Math.max(0, width - ORB_SIZE), y: clamp(position.ratio, 1) * Math.max(0, height - ORB_SIZE) }
}
export function snapOrb(x: number, y: number, width: number, height: number): OrbPosition {
  const travel = Math.max(0, height - ORB_SIZE)
  return { side: x + ORB_SIZE / 2 < width / 2 ? 'left' : 'right', ratio: travel ? clamp(y, travel) / travel : 1 }
}
