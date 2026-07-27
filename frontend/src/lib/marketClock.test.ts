/** marketClock 单元测试 */

import { beforeEach, describe, it, expect } from 'vitest'
import { resolveMarketClock, setMarketCalendarOverride } from './marketClock'

/** 构造一个在 Asia/Shanghai 下对应指定本地时间的 Date */
function shanghaiLocal(isoLocal: string): Date {
  // isoLocal: '2026-07-24T10:00:00' interpreted as Shanghai wall time
  return new Date(`${isoLocal}+08:00`)
}

describe('resolveMarketClock', () => {
  beforeEach(() => {
    setMarketCalendarOverride(null)
  })
  it('marks weekday morning as open', () => {
    const clock = resolveMarketClock(shanghaiLocal('2026-07-24T10:00:00'))
    expect(clock.isTradingDay).toBe(true)
    expect(clock.tradingDayLabel).toBe('交易日')
    expect(clock.session).toBe('morning_open')
    expect(clock.sessionLabel).toBe('开盘中（上午）')
    expect(clock.dataTradeDate).toBe('2026-07-24')
  })

  it('marks call auction window', () => {
    const clock = resolveMarketClock(shanghaiLocal('2026-07-24T09:20:00'))
    expect(clock.session).toBe('call_auction')
  })

  it('marks lunch break', () => {
    const clock = resolveMarketClock(shanghaiLocal('2026-07-24T12:00:00'))
    expect(clock.session).toBe('lunch_break')
  })

  it('marks after close on weekday', () => {
    const clock = resolveMarketClock(shanghaiLocal('2026-07-24T16:00:00'))
    expect(clock.session).toBe('after_close')
    expect(clock.sessionLabel).toBe('已收盘')
  })

  it('marks Saturday as weekend closed and rolls data trade date to Friday', () => {
    const clock = resolveMarketClock(shanghaiLocal('2026-07-25T11:00:00'))
    expect(clock.isTradingDay).toBe(false)
    expect(clock.tradingDayLabel).toBe('非交易日')
    expect(clock.session).toBe('weekend_closed')
    expect(clock.dataTradeDate).toBe('2026-07-24')
  })

  it('marks Sunday as weekend and rolls back two days', () => {
    const clock = resolveMarketClock(shanghaiLocal('2026-07-26T09:00:00'))
    expect(clock.session).toBe('weekend_closed')
    expect(clock.dataTradeDate).toBe('2026-07-24')
  })
})
