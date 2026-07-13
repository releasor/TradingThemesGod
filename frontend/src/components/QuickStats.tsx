/** 快速统计栏组件
 *
 * 显示题材总数、股票总数和最后更新时间。
 */

import { memo } from 'react'
import { Flame, BarChart3, Clock } from 'lucide-react'

interface QuickStatsProps {
  totalThemes: number
  totalStocks: number
  lastUpdate: string | null
}

export const QuickStats = memo(function QuickStats({ totalThemes, totalStocks, lastUpdate }: QuickStatsProps) {
  return (
    <div className="flex flex-wrap items-center gap-6 rounded-lg border border-border bg-card px-6 py-3">
      <div className="flex items-center gap-2 text-sm">
        <Flame className="h-4 w-4 text-orange-500" />
        <span className="text-muted-foreground">题材总数</span>
        <span className="font-semibold text-card-foreground">{totalThemes}</span>
      </div>
      <div className="flex items-center gap-2 text-sm">
        <BarChart3 className="h-4 w-4 text-blue-500" />
        <span className="text-muted-foreground">关联股票</span>
        <span className="font-semibold text-card-foreground">{totalStocks}</span>
      </div>
      <div className="flex items-center gap-2 text-sm">
        <Clock className="h-4 w-4 text-gray-500" />
        <span className="text-muted-foreground">更新时间</span>
        <span className="font-semibold text-card-foreground">
          {lastUpdate ?? '暂无数据'}
        </span>
      </div>
    </div>
  )
})
