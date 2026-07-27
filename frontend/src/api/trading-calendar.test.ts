import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from '@/api/client'
import {
  fetchCalendarStatus,
  resolveTradeDate,
  syncTradingCalendar,
} from './trading-calendar'

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

describe('trading-calendar api', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetchCalendarStatus hits status endpoint', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        source: 'akshare_sina',
        last_synced_at: null,
        row_count: 1,
        min_date: '2026-07-24',
        max_date: '2026-07-24',
        last_error: null,
        degraded: false,
        today_is_trade_day: true,
        data_trade_date: '2026-07-24',
        missing_sources: [],
      },
    })
    const status = await fetchCalendarStatus()
    expect(apiClient.get).toHaveBeenCalledWith('/market/calendar/status', {
      timeout: 8_000,
    })
    expect(status.data_trade_date).toBe('2026-07-24')
  })

  it('resolveTradeDate passes date param', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { input_date: '2026-10-05', trade_date: '2026-09-30' },
    })
    const resolved = await resolveTradeDate('2026-10-05')
    expect(apiClient.get).toHaveBeenCalledWith('/market/calendar/resolve', {
      params: { date: '2026-10-05' },
      timeout: 8_000,
    })
    expect(resolved.trade_date).toBe('2026-09-30')
  })

  it('syncTradingCalendar posts sync', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        source: 'akshare_sina',
        row_count: 10,
        degraded: false,
        data_trade_date: '2026-07-24',
        today_is_trade_day: true,
        last_synced_at: null,
        min_date: null,
        max_date: null,
        last_error: null,
        missing_sources: [],
      },
    })
    await syncTradingCalendar()
    expect(apiClient.post).toHaveBeenCalledWith('/market/calendar/sync', null, {
      timeout: 120_000,
    })
  })
})
