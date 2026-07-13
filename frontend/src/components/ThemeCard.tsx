/** 题材卡片组件
 *
 * 显示单个题材的热度、涨跌幅和关联股票数。
 * 热度指数颜色编码：红色=高热度，绿色=低热度。
 */

import { cn } from '@/lib/utils'
import { TrendingUp, TrendingDown, BarChart3 } from 'lucide-react'
import { getHeatColor, getRiseFallColor } from '@/lib/theme-colors'
import type { ThemeBrief } from '@/types/theme'

interface ThemeCardProps {
  theme: ThemeBrief
  onClick?: () => void
}

export function ThemeCard({ theme, onClick }: ThemeCardProps) {
  const heatColor = getHeatColor(Number(theme.heat_index))
  const riseFallColor = getRiseFallColor(Number(theme.rise_fall_pct))
  const isRising = Number(theme.rise_fall_pct) > 0

  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full text-left rounded-lg border border-border bg-card p-4',
        'transition-all hover:shadow-md hover:border-primary/30',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        'cursor-pointer'
      )}
    >
      {/* 主题名称 */}
      <h3 className="font-semibold text-card-foreground truncate text-sm">
        {theme.name}
      </h3>

      {/* 热度指数 */}
      <div className="mt-2 flex items-center gap-2">
        <span
          className={cn(
            'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
            heatColor
          )}
        >
          热度 {Number(theme.heat_index).toFixed(1)}
        </span>
      </div>

      {/* 涨跌幅和股票数 */}
      <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
        <span className={cn('flex items-center gap-1 font-medium', riseFallColor)}>
          {isRising ? (
            <TrendingUp className="h-3 w-3" />
          ) : (
            <TrendingDown className="h-3 w-3" />
          )}
          {Number(theme.rise_fall_pct) > 0 ? '+' : ''}
          {Number(theme.rise_fall_pct).toFixed(2)}%
        </span>
        <span className="flex items-center gap-1">
          <BarChart3 className="h-3 w-3" />
          {theme.stock_count} 只
        </span>
      </div>
    </button>
  )
}
