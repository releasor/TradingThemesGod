/** 题材表格行组件
 *
 * 显示单个题材的名称、分类、热度、股票数和涨跌幅。
 */

import { cn } from '@/lib/utils'
import { TrendingUp, TrendingDown, BarChart3 } from 'lucide-react'
import { getHeatColor, getRiseFallColor } from '@/lib/theme-colors'
import type { ThemeBrief } from '@/types/theme'

interface ThemeTableRowProps {
  theme: ThemeBrief
  onClick?: () => void
}

export function ThemeTableRow({ theme, onClick }: ThemeTableRowProps) {
  const heatValue = Number(theme.heat_index)
  const riseFallValue = Number(theme.rise_fall_pct)
  const heatColor = getHeatColor(heatValue)
  const riseFallColor = getRiseFallColor(riseFallValue)
  const isRising = riseFallValue > 0

  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full text-left rounded-lg border border-border bg-card p-4',
        'transition-all hover:shadow-md hover:border-primary/30',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        'cursor-pointer',
      )}
    >
      <div className="flex items-center justify-between gap-4">
        {/* 左侧：名称和分类 */}
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold text-card-foreground">
            {theme.name}
          </h3>
          {theme.category && (
            <span className="mt-1 inline-block rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
              {theme.category}
            </span>
          )}
        </div>

        {/* 右侧：指标 */}
        <div className="flex items-center gap-4 text-xs">
          {/* 热度 */}
          <span
            className={cn(
              'inline-flex items-center rounded-full px-2 py-0.5 font-medium',
              heatColor,
            )}
          >
            热度 {heatValue.toFixed(1)}
          </span>

          {/* 股票数 */}
          <span className="flex items-center gap-1 text-muted-foreground">
            <BarChart3 className="h-3 w-3" />
            {theme.stock_count} 只
          </span>

          {/* 涨跌幅 */}
          <span className={cn('flex items-center gap-1 font-medium', riseFallColor)}>
            {isRising ? (
              <TrendingUp className="h-3 w-3" />
            ) : (
              <TrendingDown className="h-3 w-3" />
            )}
            {riseFallValue > 0 ? '+' : ''}
            {riseFallValue.toFixed(2)}%
          </span>
        </div>
      </div>
    </button>
  )
}
