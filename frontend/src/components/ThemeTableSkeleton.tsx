/** 题材表格行骨架屏
 *
 * 加载状态下显示的占位符，与 ThemeTableRow 尺寸一致。
 * 使用 React.memo 避免父组件重渲染时不必要的更新。
 * 使用 Skeleton 组件保持一致性。
 */

import { memo } from 'react'
import { Skeleton } from '@/components/ui/skeleton'

export const ThemeTableSkeleton = memo(function ThemeTableSkeleton() {
  return (
    <div className="w-full rounded-xl border border-border bg-card p-4">
      <div className="flex items-center justify-between gap-4">
        {/* 左侧 */}
        <div className="min-w-0 flex-1">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="mt-1 h-5 w-16 rounded-full" />
        </div>

        {/* 右侧 */}
        <div className="flex items-center gap-4">
          <Skeleton className="h-5 w-20 rounded-full" />
          <Skeleton className="h-3 w-12" />
          <Skeleton className="h-3 w-16" />
        </div>
      </div>
    </div>
  )
})
