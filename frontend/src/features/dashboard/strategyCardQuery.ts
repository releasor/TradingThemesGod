import type { ShortTermPeriod, StrategyCardDataSource } from '@/types/short-term'

/** 策略卡独立缓存：database=看板题材库数据，live=策略卡专用实时爬取结果 */
export function strategyCardQueryKey(
  source: StrategyCardDataSource,
  period: ShortTermPeriod,
  startDate: string | null,
  endDate: string | null
) {
  return ['strategy-card-overview', source, period, startDate, endDate] as const
}
