/** 题材卡片骨架屏
 *
 * 加载状态下显示的占位符，与 ThemeCard 尺寸一致。
 * 使用 React.memo 避免父组件重渲染时不必要的更新。
 */

import { memo } from 'react'

export const ThemeCardSkeleton = memo(function ThemeCardSkeleton() {
  return (
    <div className="w-full rounded-lg border border-border bg-card p-4 animate-pulse">
      {/* 标题骨架 */}
      <div className="h-4 w-3/4 rounded bg-muted" />

      {/* 热度标签骨架 */}
      <div className="mt-2">
        <div className="h-5 w-20 rounded-full bg-muted" />
      </div>

      {/* 底部信息骨架 */}
      <div className="mt-3 flex items-center justify-between">
        <div className="h-3 w-16 rounded bg-muted" />
        <div className="h-3 w-12 rounded bg-muted" />
      </div>
    </div>
  )
})
