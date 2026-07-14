/** 自动刷新按钮组件

提供自动刷新功能的按钮和设置。
*/

import { memo } from 'react'
import { RefreshCw, Clock, Play, Pause } from 'lucide-react'
import { cn } from '@/lib/utils'

/** 刷新间隔选项 */
const REFRESH_INTERVALS = [
  { value: 10000, label: '10 秒' },
  { value: 30000, label: '30 秒' },
  { value: 60000, label: '1 分钟' },
  { value: 300000, label: '5 分钟' },
]

/** 自动刷新按钮属性 */
interface AutoRefreshButtonProps {
  /** 是否正在刷新 */
  isRefreshing?: boolean
  /** 是否启用自动刷新 */
  isAutoRefresh: boolean
  /** 切换自动刷新 */
  onToggleAutoRefresh: () => void
  /** 刷新间隔 */
  refreshInterval: number
  /** 设置刷新间隔 */
  onSetRefreshInterval: (interval: number) => void
  /** 手动刷新 */
  onRefresh: () => void
  /** 自定义类名 */
  className?: string
}

/**
 * 自动刷新按钮组件
 *
 * @example
 * ```tsx
 * <AutoRefreshButton
 *   isRefreshing={isFetching}
 *   isAutoRefresh={isAutoRefresh}
 *   onToggleAutoRefresh={toggleAutoRefresh}
 *   refreshInterval={refreshInterval}
 *   onSetRefreshInterval={setRefreshInterval}
 *   onRefresh={() => refetch()}
 * />
 * ```
 */
export const AutoRefreshButton = memo(function AutoRefreshButton({
  isRefreshing = false,
  isAutoRefresh,
  onToggleAutoRefresh,
  refreshInterval,
  onSetRefreshInterval,
  onRefresh,
  className,
}: AutoRefreshButtonProps) {
  return (
    <div className={cn('flex items-center gap-2', className)}>
      {/* 手动刷新按钮 */}
      <button
        onClick={onRefresh}
        disabled={isRefreshing}
        className="inline-flex items-center gap-2 rounded-md border border-border bg-card px-3 py-2 text-sm font-medium text-card-foreground transition-colors hover:bg-accent disabled:opacity-50"
      >
        <RefreshCw className={cn('h-4 w-4', isRefreshing && 'animate-spin')} />
        刷新
      </button>

      {/* 自动刷新切换 */}
      <button
        onClick={onToggleAutoRefresh}
        className={cn(
          'inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium transition-colors',
          isAutoRefresh
            ? 'border-primary bg-primary text-primary-foreground hover:bg-primary/90'
            : 'border-border bg-card text-card-foreground hover:bg-accent'
        )}
        title={isAutoRefresh ? '停止自动刷新' : '开启自动刷新'}
      >
        {isAutoRefresh ? (
          <Pause className="h-4 w-4" />
        ) : (
          <Play className="h-4 w-4" />
        )}
        自动刷新
      </button>

      {/* 刷新间隔选择 */}
      {isAutoRefresh && (
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-muted-foreground" />
          <select
            value={refreshInterval}
            onChange={(e) => onSetRefreshInterval(Number(e.target.value))}
            className="rounded border border-input bg-background px-2 py-1 text-sm"
          >
            {REFRESH_INTERVALS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  )
})
