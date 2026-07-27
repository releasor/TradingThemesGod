/** 交易日历 API */

import { apiClient } from '@/api/client'
import type {
  TradingCalendarResolve,
  TradingCalendarStatus,
} from '@/types/trading-calendar'

export async function fetchCalendarStatus(): Promise<TradingCalendarStatus> {
  const { data } = await apiClient.get<TradingCalendarStatus>('/market/calendar/status', {
    timeout: 8_000,
  })
  return data
}

export async function resolveTradeDate(
  date?: string
): Promise<TradingCalendarResolve> {
  const { data } = await apiClient.get<TradingCalendarResolve>('/market/calendar/resolve', {
    params: date ? { date } : {},
    timeout: 8_000,
  })
  return data
}

export async function syncTradingCalendar(): Promise<TradingCalendarStatus> {
  const { data } = await apiClient.post<TradingCalendarStatus>(
    '/market/calendar/sync',
    null,
    { timeout: 120_000 }
  )
  return data
}
