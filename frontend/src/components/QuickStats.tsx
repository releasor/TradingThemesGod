/** 快速统计栏组件
 *
 * 显示题材总数、股票总数和行情更新时间。
 */

import { memo, type ReactNode } from 'react'
import { Flame, BarChart3, Clock } from 'lucide-react'
import { GlowCard } from '@/components/GlowCard'

interface QuickStatsProps {
  totalThemes: number
  totalStocks: number
  lastUpdate: string | null
  actions?: ReactNode
}

export const QuickStats = memo(function QuickStats({
  totalThemes,
  totalStocks,
  lastUpdate,
  actions,
}: QuickStatsProps) {
  return (
    <GlowCard>
      <div
        className="flex flex-wrap items-center gap-6 px-6 py-3"
        data-testid="quick-stats"
      >
        <div
          className="flex items-center gap-2 text-sm"
          title="真实题材数量（已排除市场表现与行情指标板块）"
        >
          <Flame className="h-4 w-4 text-orange-500" />
          <span className="text-muted-foreground">题材总数</span>
          <span className="font-semibold text-card-foreground">{totalThemes}</span>
        </div>
        <div className="flex items-center gap-2 text-sm" title="股票库去重总数，不是热门榜成分股加总">
          <BarChart3 className="h-4 w-4 text-blue-500" />
          <span className="text-muted-foreground">股票总数</span>
          <span className="font-semibold text-card-foreground">{totalStocks}</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <Clock className="h-4 w-4 text-gray-500" />
          <span className="text-muted-foreground">行情更新</span>
          <span className="font-semibold text-card-foreground">
            {lastUpdate ?? '暂无数据'}
          </span>
        </div>
        {actions ? <div className="ml-auto">{actions}</div> : null}
      </div>
    </GlowCard>
  )
})
