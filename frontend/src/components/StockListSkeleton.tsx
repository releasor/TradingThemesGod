/** 股票列表骨架屏
 *
 * 加载状态占位符，匹配 StockList 样式。
 * 使用 React.memo 避免父组件重渲染时不必要的更新。
 */

import { memo } from 'react'
import { Skeleton } from '@/components/ui/skeleton'

export const StockListSkeleton = memo(function StockListSkeleton() {
  return (
    <div className="space-y-1">
      {Array.from({ length: 3 }).map((_, i) => (
        <div
          key={i}
          className="flex items-center justify-between rounded-xl px-2 py-1.5"
        >
          <div className="flex items-center gap-2">
            <Skeleton className="h-3.5 w-12" />
            <Skeleton className="h-3.5 w-16" />
          </div>
          <Skeleton className="h-3.5 w-14" />
        </div>
      ))}
    </div>
  )
})
