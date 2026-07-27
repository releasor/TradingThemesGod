/** 交易日历 API 类型 */

export interface TradingCalendarStatus {
  source: string
  last_synced_at: string | null
  row_count: number
  min_date: string | null
  max_date: string | null
  last_error: string | null
  degraded: boolean
  today_is_trade_day: boolean
  data_trade_date: string
  missing_sources: string[]
}

export interface TradingCalendarResolve {
  input_date: string
  trade_date: string
}
