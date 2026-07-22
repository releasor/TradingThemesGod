/** 题材卡片组件
 *
 * 显示单个题材的热度、涨跌幅和关联股票数。
 * 热度指数颜色编码：红色=高热度，绿色=低热度。
 * 使用 React.memo 优化列表渲染性能。
 */

import { memo } from 'react'
import { cn } from '@/lib/utils'
import { TrendingUp, TrendingDown, BarChart3 } from 'lucide-react'
import { getHeatColor, getRiseFallColor } from '@/lib/theme-colors'
import { usePrefetchTheme } from '@/hooks/usePrefetch'
import { GlowCard } from '@/components/GlowCard'
import type { ThemeBrief } from '@/types/theme'

interface ThemeCardProps {
  theme: ThemeBrief
  onClick?: () => void
}

export const ThemeCard = memo(function ThemeCard({ theme, onClick }: ThemeCardProps) {
  const heatValue = Number(theme.heat_index)
  const riseFallValue = Number(theme.rise_fall_pct)
  const heatColor = getHeatColor(heatValue)
  const riseFallColor = getRiseFallColor(riseFallValue)
  const isRising = riseFallValue > 0
  const prefetchTheme = usePrefetchTheme()

  return (
    <GlowCard className="w-full">
      <button
        onClick={onClick}
        onMouseEnter={() => prefetchTheme(theme.id)}
        className={cn(
          'w-full cursor-pointer p-4 text-left',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
        )}
        aria-label={`查看题材详情: ${theme.name}`}
      >
        <h3 className="truncate text-sm font-semibold text-card-foreground">{theme.name}</h3>

        <div className="mt-2 flex items-center gap-2">
          <span
            className={cn(
              'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
              heatColor
            )}
          >
            热度 {heatValue.toFixed(1)}
          </span>
        </div>

        <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
          <span className={cn('flex items-center gap-1 font-medium', riseFallColor)}>
            {isRising ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
            {riseFallValue > 0 ? '+' : ''}
            {riseFallValue.toFixed(2)}%
          </span>
          <span className="flex items-center gap-1">
            <BarChart3 className="h-3 w-3" />
            {theme.stock_count} 只
          </span>
        </div>
      </button>
    </GlowCard>
  )
})
