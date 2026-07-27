/** 看板顶部刷新控件：轻量刷新、全量更新、取消（无自动刷新） */

import { memo } from 'react'
import { RefreshCw, Database, X } from 'lucide-react'
import { cn } from '@/lib/utils'

interface DashboardRefreshControlsProps {
  /** 是否正在轻量刷新 */
  isRefreshing?: boolean
  /** 是否正在全量更新（爬虫） */
  isUpdating?: boolean
  /** 轻量刷新：仅重新拉取看板接口 */
  onRefresh: () => void
  /** 全量更新：触发爬虫采集（可选） */
  onFullUpdate?: () => void
  /** 取消进行中的刷新或全量更新 */
  onCancel: () => void
  /** 轻量刷新已耗时文案 */
  refreshElapsedLabel?: string
  /** 全量更新已耗时文案 */
  updateElapsedLabel?: string
  /** 自定义类名 */
  className?: string
}

export const DashboardRefreshControls = memo(function DashboardRefreshControls({
  isRefreshing = false,
  isUpdating = false,
  onRefresh,
  onFullUpdate,
  onCancel,
  refreshElapsedLabel,
  updateElapsedLabel,
  className,
}: DashboardRefreshControlsProps) {
  const busy = isRefreshing || isUpdating

  return (
    <div className={cn('flex flex-wrap items-center gap-2', className)}>
      <button
        type="button"
        onClick={onRefresh}
        disabled={busy}
        title="快刷题材涨跌幅、策略卡与看板，不抓取成分股；成分股全量请用「全量更新」"
        className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-3 py-2 text-sm font-medium text-card-foreground transition-colors hover:bg-accent disabled:opacity-50"
      >
        <RefreshCw className={cn('h-4 w-4', isRefreshing && 'animate-spin')} />
        {isRefreshing && refreshElapsedLabel ? `刷新中 ${refreshElapsedLabel}` : '刷新'}
      </button>

      {onFullUpdate && (
        <button
          type="button"
          onClick={onFullUpdate}
          disabled={busy}
          title="从数据源全量采集，通常需要较长时间"
          className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-3 py-2 text-sm font-medium text-card-foreground transition-colors hover:bg-accent disabled:opacity-50"
        >
          <Database className={cn('h-4 w-4', isUpdating && 'animate-pulse')} />
          {isUpdating
            ? updateElapsedLabel
              ? `全量更新中 ${updateElapsedLabel}`
              : '全量更新中…'
            : '全量更新'}
        </button>
      )}

      {busy && (
        <button
          type="button"
          onClick={onCancel}
          title="取消进行中的刷新"
          className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-3 py-2 text-sm font-medium text-card-foreground transition-colors hover:bg-accent"
        >
          <X className="h-4 w-4" />
          取消
        </button>
      )}
    </div>
  )
})
