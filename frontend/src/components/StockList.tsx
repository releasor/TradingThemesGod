/** 股票列表组件
 *
 * 展开链路点后显示关联的股票列表。
 * 每个股票可点击打开 StockPopover。
 */

import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { StockPopover } from '@/components/StockPopover'
import { getRiseFallColor } from '@/lib/theme-colors'
import type { StockBrief } from '@/types/stock'

interface StockListProps {
  stocks: StockBrief[]
}

/** 格式化涨跌幅显示 */
function formatRiseFall(pct: number | null): string {
  if (pct === null) return '-'
  const sign = pct > 0 ? '+' : ''
  return `${sign}${pct.toFixed(2)}%`
}

export function StockList({ stocks }: StockListProps) {
  if (stocks.length === 0) {
    return (
      <div className="py-2 text-center text-xs text-muted-foreground">
        暂无关联股票
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {stocks.map((stock) => (
        <StockPopover key={stock.code} stock={stock}>
          <button className="flex w-full items-center justify-between rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-accent">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-muted-foreground">
                {stock.code}
              </span>
              <span className="text-foreground">{stock.name}</span>
            </div>
            <span
              className={`flex items-center gap-1 text-xs font-medium ${getRiseFallColor(
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
}
