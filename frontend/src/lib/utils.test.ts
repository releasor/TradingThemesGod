import { describe, it, expect } from 'vitest'
import { formatRiseFall, formatMarketCap } from './utils'

describe('formatRiseFall', () => {
  it('formats positive value with + prefix', () => {
    expect(formatRiseFall(5.23)).toBe('+5.23%')
  })

  it('formats negative value', () => {
    expect(formatRiseFall(-3.14)).toBe('-3.14%')
  })

  it('formats zero without sign', () => {
    expect(formatRiseFall(0)).toBe('0.00%')
  })

  it('returns "-" for null', () => {
    expect(formatRiseFall(null)).toBe('-')
  })

  it('returns "-" for undefined', () => {
    expect(formatRiseFall(undefined)).toBe('-')
  })

  it('formats large positive value', () => {
    expect(formatRiseFall(123.45)).toBe('+123.45%')
  })

  it('formats very small negative value', () => {
    expect(formatRiseFall(-0.01)).toBe('-0.01%')
  })
})

describe('formatMarketCap', () => {
  it('formats value in 亿', () => {
    expect(formatMarketCap(1_0000_0000)).toBe('1.00亿')
  })

  it('formats large value in 亿', () => {
    expect(formatMarketCap(5_5000_0000)).toBe('5.50亿')
  })

  it('formats value in 万', () => {
    expect(formatMarketCap(1_0000)).toBe('1.00万')
  })

  it('formats medium value in 万', () => {
    expect(formatMarketCap(50_0000)).toBe('50.00万')
  })

  it('formats small value directly', () => {
    expect(formatMarketCap(9999)).toBe('9999.00')
  })

  it('returns "-" for null', () => {
    expect(formatMarketCap(null)).toBe('-')
  })

  it('returns "-" for undefined', () => {
    expect(formatMarketCap(undefined)).toBe('-')
  })

  it('formats zero directly', () => {
    expect(formatMarketCap(0)).toBe('0.00')
  })

  it('formats exactly 万 threshold', () => {
    expect(formatMarketCap(10000)).toBe('1.00万')
  })

  it('formats exactly 亿 threshold', () => {
    expect(formatMarketCap(1_0000_0000)).toBe('1.00亿')
  })
})
