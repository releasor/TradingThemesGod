/** 股票列表骨架屏
 *
 * 加载状态占位符，匹配 StockList 样式。
 * 使用 React.memo 避免父组件重渲染时不必要的更新。
 */

import { memo } from 'react'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

interface StockListSkeletonProps {
  layout?: 'stack' | 'grid'
}

export const StockListSkeleton = memo(function StockListSkeleton({
  layout = 'stack',
}: StockListSkeletonProps) {
  const count = layout === 'grid' ? 9 : 3
  return (
    <div
      className={cn(
        layout === 'grid'
          ? 'grid grid-cols-1 gap-1.5 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4'
          : 'space-y-1'
      )}
    >
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className={cn(
            'flex items-center justify-between rounded-xl px-2.5 py-1.5',
            layout === 'grid' && 'border border-border/60'
          )}
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
