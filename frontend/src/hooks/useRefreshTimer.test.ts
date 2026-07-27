import { describe, expect, it } from 'vitest'
import { formatRefreshDurationMs, quoteSourceLabel } from './useRefreshTimer'

describe('useRefreshTimer helpers', () => {
  it('formats millisecond duration', () => {
    expect(formatRefreshDurationMs(1500)).toBe('2 秒')
    expect(formatRefreshDurationMs(65000)).toBe('1 分 5 秒')
  })

  it('maps quote source labels', () => {
    expect(quoteSourceLabel('eastmoney')).toBe('东方财富')
    expect(quoteSourceLabel('akshare')).toBe('AKShare')
  })
})
