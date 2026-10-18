import { describe, expect, it } from 'vitest'
import { orbPoint, snapOrb, parseOrbPosition } from '../../utils/assistant/orb'

describe('assistant orb position', () => {
  it('rejects corrupt preferences and clamps restored positions across viewport sizes', () => {
    for (const raw of [null, '{', 'null', '{}', '{"side":"top","ratio":0.5}', '{"side":"left","ratio":"0.5"}']) {
      expect(parseOrbPosition(raw)).toEqual({ side: 'right', ratio: 1 })
    }
    expect(parseOrbPosition('{"side":"left","ratio":-2}')).toEqual({ side: 'left', ratio: 0 })
    expect(parseOrbPosition('{"side":"right","ratio":8}')).toEqual({ side: 'right', ratio: 1 })
    for (const [width, height] of [[288, 700], [1200, 600], [52, 52], [30, 30]]) {
      const point = orbPoint({ side: 'right', ratio: 0.5 }, width!, height!)
      expect(point.x).toBeGreaterThanOrEqual(0)
      expect(point.x).toBeLessThanOrEqual(Math.max(0, width! - 52))
      expect(point.y).toBeGreaterThanOrEqual(0)
      expect(point.y).toBeLessThanOrEqual(Math.max(0, height! - 52))
    }
  })
  it('snaps by the ball center and preserves relative vertical placement', () => {
    expect(snapOrb(50, 100, 300, 452)).toEqual({ side: 'left', ratio: 0.25 })
    expect(snapOrb(200, 900, 300, 452)).toEqual({ side: 'right', ratio: 1 })
    expect(snapOrb(50, -20, 300, 452)).toEqual({ side: 'left', ratio: 0 })
    expect(orbPoint(snapOrb(50, 100, 300, 452), 500, 852)).toEqual({ x: 0, y: 200 })
    expect(snapOrb(0, 0, 52, 52).ratio).toBe(1)
  })
})
