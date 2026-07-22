import { Activity, ArrowDown, ArrowUp, Ban, Minus } from 'lucide-react'

import { cn } from '@/lib/utils'
import type { ThemeMarketSnapshot } from '@/types/theme'

interface ThemeMarketBreadthProps {
  snapshot: ThemeMarketSnapshot | null
  className?: string
}

export function ThemeMarketBreadth({ snapshot, className }: ThemeMarketBreadthProps) {
  if (!snapshot) {
    return (
      <section
        className={cn('border-y border-border py-5 text-sm text-muted-foreground', className)}
      >
        暂无行情统计
      </section>
    )
  }
  const items = [
    { label: '涨停', value: snapshot.limit_up_count, icon: ArrowUp, tone: 'text-red-600' },
    { label: '跌停', value: snapshot.limit_down_count, icon: ArrowDown, tone: 'text-emerald-600' },
    { label: '上涨', value: snapshot.up_count, icon: ArrowUp, tone: 'text-red-600' },
    { label: '下跌', value: snapshot.down_count, icon: ArrowDown, tone: 'text-emerald-600' },
  ]
  return (
    <section
      aria-labelledby="market-breadth-heading"
      className={cn('border-y border-border py-5', className)}
    >
      <div className="mb-4 flex items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-widest text-muted-foreground">Market breadth</p>
          <h2 id="market-breadth-heading" className="mt-1 text-lg font-semibold">
            题材市场广度
          </h2>
        </div>
        <time className="text-xs tabular-nums text-muted-foreground">{snapshot.trade_date}</time>
      </div>
      <div className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-border bg-border sm:grid-cols-5">
        {items.map(({ label, value, icon: Icon, tone }) => (
          <div key={label} className="bg-card p-4">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Icon className={cn('h-3.5 w-3.5', tone)} />
              {label}
            </div>
            <strong
              data-testid={
                label === '涨停'
                  ? 'limit-up-count'
                  : label === '跌停'
                    ? 'limit-down-count'
                    : undefined
              }
              className={cn('mt-2 block text-xl tabular-nums', tone)}
            >
              {value ?? '暂无数据'}
            </strong>
          </div>
        ))}
        <div className="col-span-2 bg-card p-4 sm:col-span-1">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Activity className="h-3.5 w-3.5" />
            上涨:下跌
          </div>
          <strong className="mt-2 block text-xl tabular-nums">{snapshot.up_down_display}</strong>
          <span className="text-xs text-muted-foreground">
            {snapshot.up_down_ratio === null
              ? '暂无'
              : `比值${snapshot.up_down_ratio.toFixed(2)}`}
          </span>
        </div>
      </div>
      <p className="mt-3 flex gap-4 text-xs text-muted-foreground">
        <span>
          <Minus className="mr-1 inline h-3 w-3" />
          平盘 {snapshot.flat_count}
        </span>
        <span>
          <Ban className="mr-1 inline h-3 w-3" />
          停牌/无行情{snapshot.suspended_count}
        </span>
      </p>
    </section>
  )
}
