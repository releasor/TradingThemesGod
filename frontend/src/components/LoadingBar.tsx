/** 加载进度条组件
 *
 * 在页面顶部显示一个动画进度条，用于指示数据加载状态。
 * 使用 CSS 动画实现平滑的进度条效果。
 */

import { memo } from 'react'
import { cn } from '@/lib/utils'

interface LoadingBarProps {
  /** 是否正在加载 */
  isLoading: boolean
}

export const LoadingBar = memo(function LoadingBar({ isLoading }: LoadingBarProps) {
  if (!isLoading) return null

  return (
    <div className="fixed top-0 left-0 right-0 z-50 h-0.5">
      <div
        className={cn(
          'h-full bg-primary',
          'animate-loading-bar',
        )}
        style={{
          animation: 'loading-bar 1.5s ease-in-out infinite',
        }}
      />
    </div>
  )
})
