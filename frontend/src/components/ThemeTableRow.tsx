/** 题材表格行组件
 *
 * 显示单个题材的名称、分类、热度、股票数和涨跌幅。
 * 使用 React.memo 优化列表渲染性能。
 * 支持悬停高亮和点击反馈。
 */

import { memo, useState } from 'react'
import { cn } from '@/lib/utils'
import { TrendingUp, TrendingDown, BarChart3, ChevronRight } from 'lucide-react'
import { getHeatColor, getRiseFallColor } from '@/lib/theme-colors'
import { GlowCard } from '@/components/GlowCard'
import { ThemeLifecycleBadge } from '@/components/ThemeLifecycleBadge'
import type { ThemeBrief } from '@/types/theme'

interface ThemeTableRowProps {
  theme: ThemeBrief
  onClick?: () => void
}

export const ThemeTableRow = memo(function ThemeTableRow({ theme, onClick }: ThemeTableRowProps) {
  const [isPressed, setIsPressed] = useState(false)
  const heatValue = Number(theme.heat_index)
  const riseFallValue = Number(theme.rise_fall_pct)
  const heatColor = getHeatColor(heatValue)
  const riseFallColor = getRiseFallColor(riseFallValue)
  const isRising = riseFallValue > 0

  return (
    <GlowCard className="w-full">
      <button
        onClick={onClick}
        onMouseDown={() => setIsPressed(true)}
        onMouseUp={() => setIsPressed(false)}
        onMouseLeave={() => setIsPressed(false)}
        className={cn(
          'group w-full cursor-pointer p-4 text-left transition-all duration-200',
          'hover:bg-accent/50',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          'active:scale-[0.99]',
          isPressed && 'scale-[0.99]'
        )}
        aria-label={`查看题材详情: ${theme.name}`}
      >
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h3 className="truncate text-sm font-semibold text-card-foreground transition-colors group-hover:text-primary">
                {theme.name}
              </h3>
              <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
            </div>
            {theme.category && (
              <span className="mt-1 inline-block rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                {theme.category}
              </span>
            )}
            <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
              <ThemeLifecycleBadge stage={theme.lifecycle_stage} />
              {typeof theme.strength_score === 'number' && (
                <span className="text-[11px] tabular-nums text-muted-foreground">
                  强度 {theme.strength_score}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs">
            <span
              className={cn(
                'inline-flex items-center rounded-full px-2 py-0.5 font-medium',
                heatColor
              )}
            >
              热度 {heatValue.toFixed(1)}
            </span>

            <span className="flex items-center gap-1 text-muted-foreground">
              <BarChart3 className="h-3 w-3" />
              {theme.stock_count} 只
            </span>

            <span className={cn('flex items-center gap-1 font-medium', riseFallColor)}>
              {isRising ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
              {riseFallValue > 0 ? '+' : ''}
              {riseFallValue.toFixed(2)}%
            </span>
          </div>
        </div>
      </button>
    </GlowCard>
  )
})
