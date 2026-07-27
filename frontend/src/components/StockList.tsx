/** 股票列表组件
 *
 * 展开链路点后显示关联的股票列表。
 * 每个股票可点击打开 StockPopover。
 */

import { memo } from 'react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { StockPopover } from '@/components/StockPopover'
import { getRiseFallColor } from '@/lib/theme-colors'
import { cn, formatRiseFall } from '@/lib/utils'
import type { StockBrief } from '@/types/stock'

interface StockListProps {
  stocks: StockBrief[]
  /** stack=单列（链路点）；grid=多列紧凑（题材全部成分股） */
  layout?: 'stack' | 'grid'
}

export const StockList = memo(function StockList({
  stocks,
  layout = 'stack',
}: StockListProps) {
  if (stocks.length === 0) {
    return (
      <div className="py-2 text-center text-xs text-muted-foreground">
        暂无关联股票
      </div>
    )
  }

  return (
    <div
      data-testid="stock-list"
      data-layout={layout}
      className={cn(
        layout === 'grid'
          ? 'grid grid-cols-1 gap-1.5 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4'
          : 'space-y-1'
      )}
    >
      {stocks.map((stock) => (
        <StockPopover key={stock.code} stock={stock}>
          <button
            type="button"
            className={cn(
              'flex w-full items-center justify-between gap-2 rounded-xl px-2.5 py-1.5 text-left text-sm transition-colors hover:bg-accent',
              layout === 'grid' && 'border border-border/60 bg-background/40'
            )}
          >
            <div className="flex min-w-0 items-center gap-2">
              <span className="shrink-0 font-mono text-xs text-muted-foreground">
                {stock.code}
              </span>
              <span className="truncate text-foreground">{stock.name}</span>
            </div>
            <span
              className={`flex shrink-0 items-center gap-1 text-xs font-medium ${getRiseFallColor(
                stock.rise_fall_pct ?? 0
              )}`}
            >
              {stock.rise_fall_pct !== null && stock.rise_fall_pct > 0 && (
                <TrendingUp className="h-3 w-3" />
              )}
              {stock.rise_fall_pct !== null && stock.rise_fall_pct < 0 && (
                <TrendingDown className="h-3 w-3" />
              )}
              {stock.rise_fall_pct !== null && stock.rise_fall_pct === 0 && (
                <Minus className="h-3 w-3" />
              )}
              {formatRiseFall(stock.rise_fall_pct)}
            </span>
          </button>
        </StockPopover>
      ))}
    </div>
  )
})
