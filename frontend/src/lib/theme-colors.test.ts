import { describe, it, expect } from 'vitest'
import { getHeatColor, getRiseFallColor } from './theme-colors'

describe('getHeatColor', () => {
  it('returns red for heat >= 80', () => {
    expect(getHeatColor(80)).toBe('text-red-600 bg-red-50')
    expect(getHeatColor(100)).toBe('text-red-600 bg-red-50')
  })

  it('returns orange for heat >= 60 and < 80', () => {
    expect(getHeatColor(60)).toBe('text-orange-600 bg-orange-50')
    expect(getHeatColor(79)).toBe('text-orange-600 bg-orange-50')
  })

  it('returns yellow for heat >= 40 and < 60', () => {
    expect(getHeatColor(40)).toBe('text-yellow-600 bg-yellow-50')
    expect(getHeatColor(59)).toBe('text-yellow-600 bg-yellow-50')
  })

  it('returns green for heat < 40', () => {
    expect(getHeatColor(0)).toBe('text-green-600 bg-green-50')
    expect(getHeatColor(39)).toBe('text-green-600 bg-green-50')
  })
})

describe('getRiseFallColor', () => {
  it('returns red for positive pct', () => {
    expect(getRiseFallColor(1.5)).toBe('text-red-600')
    expect(getRiseFallColor(0.01)).toBe('text-red-600')
  })

  it('returns green for negative pct', () => {
    expect(getRiseFallColor(-1.5)).toBe('text-green-600')
    expect(getRiseFallColor(-0.01)).toBe('text-green-600')
  })

  it('returns muted for zero pct', () => {
    expect(getRiseFallColor(0)).toBe('text-muted-foreground')
  })
})
