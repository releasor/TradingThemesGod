/** 加载进度条组件
 *
 * 在页面顶部显示一个动画进度条，用于指示数据加载状态。
 * 使用 CSS 动画实现平滑的进度条效果；传入 progress 时改为确定进度。
 */

import { memo } from 'react'
import { cn } from '@/lib/utils'

interface LoadingBarProps {
  /** 是否正在加载 */
  isLoading: boolean
  /** 0–100 确定进度；未传则使用不确定动画 */
  progress?: number | null
}

export const LoadingBar = memo(function LoadingBar({ isLoading, progress }: LoadingBarProps) {
  if (!isLoading) return null

  const determinate =
    typeof progress === 'number' && Number.isFinite(progress)
      ? Math.min(100, Math.max(0, progress))
      : null

  return (
    <div className="fixed top-0 left-0 right-0 z-50 h-1.5 bg-muted/40">
      <div
        className={cn(
          // 暗色主题 --primary 接近白，勿用 bg-primary，否则顶部像一条白线
          'h-full bg-sky-500',
          determinate === null && 'animate-loading-bar'
        )}
        style={
          determinate === null
            ? {
                animation: 'loading-bar 1.5s ease-in-out infinite',
              }
            : {
                width: `${determinate}%`,
                transition: 'width 200ms ease-out',
              }
        }
        data-testid={determinate === null ? undefined : 'loading-bar-progress'}
      />
    </div>
  )
})
