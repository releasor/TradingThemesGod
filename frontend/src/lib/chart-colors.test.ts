import { describe, it, expect } from 'vitest'
import {
  CHART_COLOR_PALETTE,
  RISE_FALL_COLORS,
  CHAIN_LEVEL_COLORS,
  getChartThemeColors,
} from './chart-colors'

describe('CHART_COLOR_PALETTE', () => {
  it('contains 10 colors', () => {
    expect(CHART_COLOR_PALETTE).toHaveLength(10)
  })

  it('all colors are valid hex format', () => {
    for (const color of CHART_COLOR_PALETTE) {
      expect(color).toMatch(/^#[0-9a-f]{6}$/i)
    }
  })

  it('all colors are unique', () => {
    const unique = new Set(CHART_COLOR_PALETTE)
    expect(unique.size).toBe(CHART_COLOR_PALETTE.length)
  })
})

describe('RISE_FALL_COLORS', () => {
  it('has rise, fall, and neutral colors', () => {
    expect(RISE_FALL_COLORS).toHaveProperty('rise')
    expect(RISE_FALL_COLORS).toHaveProperty('fall')
    expect(RISE_FALL_COLORS).toHaveProperty('neutral')
  })

  it('rise is red (Chinese stock convention)', () => {
    // 红涨绿跌
    expect(RISE_FALL_COLORS.rise).toBe('#ef4444')
  })

  it('fall is green (Chinese stock convention)', () => {
    expect(RISE_FALL_COLORS.fall).toBe('#22c55e')
  })

  it('neutral is gray', () => {
    expect(RISE_FALL_COLORS.neutral).toBe('#9ca3af')
  })
})

describe('CHAIN_LEVEL_COLORS', () => {
  it('has upstream, midstream, downstream colors', () => {
    expect(CHAIN_LEVEL_COLORS).toHaveProperty('upstream')
    expect(CHAIN_LEVEL_COLORS).toHaveProperty('midstream')
    expect(CHAIN_LEVEL_COLORS).toHaveProperty('downstream')
  })

  it('all colors are valid hex format', () => {
    for (const color of Object.values(CHAIN_LEVEL_COLORS)) {
      expect(color).toMatch(/^#[0-9a-f]{6}$/i)
    }
  })

  it('all level colors are distinct', () => {
    const colors = Object.values(CHAIN_LEVEL_COLORS)
    const unique = new Set(colors)
    expect(unique.size).toBe(colors.length)
  })
})

describe('getChartThemeColors', () => {
  it('returns light theme colors when isDark is false', () => {
    const colors = getChartThemeColors(false)
    expect(colors.textColor).toBe('#374151')
    expect(colors.secondaryTextColor).toBe('#6b7280')
    expect(colors.gridBorderColor).toBe('#e5e7eb')
    expect(colors.backgroundColor).toBe('transparent')
    expect(colors.tooltipBg).toBe('#ffffff')
    expect(colors.tooltipTextColor).toBe('#374151')
    expect(colors.tooltipBorderColor).toBe('#e5e7eb')
  })

  it('returns dark theme colors when isDark is true', () => {
    const colors = getChartThemeColors(true)
    expect(colors.textColor).toBe('#e5e7eb')
    expect(colors.secondaryTextColor).toBe('#9ca3af')
    expect(colors.gridBorderColor).toBe('#374151')
    expect(colors.backgroundColor).toBe('transparent')
    expect(colors.tooltipBg).toBe('#1f2937')
    expect(colors.tooltipTextColor).toBe('#e5e7eb')
    expect(colors.tooltipBorderColor).toBe('#4b5563')
  })

  it('always uses transparent background', () => {
    expect(getChartThemeColors(false).backgroundColor).toBe('transparent')
    expect(getChartThemeColors(true).backgroundColor).toBe('transparent')
  })

  it('returns all required keys', () => {
    const colors = getChartThemeColors(true)
    expect(colors).toHaveProperty('textColor')
    expect(colors).toHaveProperty('secondaryTextColor')
    expect(colors).toHaveProperty('gridBorderColor')
    expect(colors).toHaveProperty('backgroundColor')
    expect(colors).toHaveProperty('tooltipBg')
    expect(colors).toHaveProperty('tooltipTextColor')
    expect(colors).toHaveProperty('tooltipBorderColor')
  })
})
