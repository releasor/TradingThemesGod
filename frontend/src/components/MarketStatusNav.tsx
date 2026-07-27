/** 顶栏左侧：北京时间 / 交易日 / 市场状态（三行透明卡片，与右侧账号顶对齐） */

import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Activity, CalendarClock, Clock } from 'lucide-react'

import { fetchCalendarStatus } from '@/api/trading-calendar'
import {
  resolveMarketClock,
  setMarketCalendarOverride,
  type MarketClockInfo,
} from '@/lib/marketClock'
import { cn } from '@/lib/utils'

export function MarketStatusNav({ className = '' }: { className?: string }) {
  const [clock, setClock] = useState<MarketClockInfo>(() => resolveMarketClock())

  const calendarQuery = useQuery({
    queryKey: ['market', 'calendar', 'status'],
    queryFn: fetchCalendarStatus,
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
  })

  useEffect(() => {
    if (!calendarQuery.data) return
    setMarketCalendarOverride({
      isTradingDay: calendarQuery.data.today_is_trade_day,
      dataTradeDate: calendarQuery.data.data_trade_date,
    })
    setClock(resolveMarketClock())
  }, [calendarQuery.data])

  useEffect(() => {
    const tick = () => setClock(resolveMarketClock())
    tick()
    const id = window.setInterval(tick, 1000)
    return () => window.clearInterval(id)
  }, [])

  return (
    <div
      className={cn(
        'flex flex-col gap-1 rounded-xl border border-border/70 bg-background/70 px-3 py-2 text-xs shadow-sm backdrop-blur-sm sm:text-sm',
        className
      )}
      data-testid="market-status-nav"
    >
      <div className="flex min-h-5 items-center gap-1.5" title="北京时间">
        <Clock className="h-3.5 w-3.5 shrink-0 text-sky-500" />
        <span className="shrink-0 text-muted-foreground">当前时间</span>
        <span
          className="font-medium tabular-nums text-foreground"
          data-testid="market-now"
        >
          {clock.nowText}
        </span>
      </div>
      <div
        className="flex min-h-5 items-center gap-1.5"
        title={
          clock.isTradingDay
            ? '按服务端 A 股交易日历判断开市日'
            : `非开市日，数据交易日回退为 ${clock.dataTradeDate}`
        }
      >
        <CalendarClock className="h-3.5 w-3.5 shrink-0 text-emerald-500" />
        <span className="shrink-0 text-muted-foreground">交易日</span>
        <span className="font-medium text-foreground" data-testid="trading-day-label">
          {clock.tradingDayLabel}
        </span>
        {!clock.isTradingDay ? (
          <span className="text-muted-foreground">· 数据日 {clock.dataTradeDate}</span>
        ) : null}
      </div>
      <div
        className="flex min-h-5 items-center gap-1.5"
        title="按沪深常规时段（含集合竞价/午休）"
      >
        <Activity className="h-3.5 w-3.5 shrink-0 text-amber-500" />
        <span className="shrink-0 text-muted-foreground">市场状态</span>
        <span className="font-medium text-foreground" data-testid="market-session">
          {clock.sessionLabel}
        </span>
      </div>
    </div>
  )
}
