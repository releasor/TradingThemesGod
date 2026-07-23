/** 自动刷新按钮组件

提供轻量刷新、全量更新和自动刷新设置。
*/

import { memo } from 'react'
import { RefreshCw, Clock, Play, Pause, Database } from 'lucide-react'
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
  /** 是否正在轻量刷新 */
  isRefreshing?: boolean
  /** 是否正在全量更新（爬虫） */
  isUpdating?: boolean
  /** 是否启用自动刷新 */
  isAutoRefresh: boolean
  /** 切换自动刷新 */
  onToggleAutoRefresh: () => void
  /** 刷新间隔 */
  refreshInterval: number
  /** 设置刷新间隔 */
  onSetRefreshInterval: (interval: number) => void
  /** 轻量刷新：仅重新拉取看板接口 */
  onRefresh: () => void
  /** 全量更新：触发爬虫采集（可选） */
  onFullUpdate?: () => void
  /** 看板可选数据源 */
  scraperSources?: ScraperSourceOption[]
  /** 当前选中的数据源 */
  selectedScraperSource?: string
  /** 切换数据源 */
  onScraperSourceChange?: (source: string) => void
  /** 自定义类名 */
  className?: string
}

export interface ScraperSourceOption {
  id: string
  label: string
  description: string
}

/**
 * 自动刷新按钮组件
 *
 * @example
 * ```tsx
 * <AutoRefreshButton
 *   isRefreshing={isFetching}
 *   isUpdating={isUpdating}
 *   isAutoRefresh={isAutoRefresh}
 *   onToggleAutoRefresh={toggleAutoRefresh}
 *   refreshInterval={refreshInterval}
 *   onSetRefreshInterval={setRefreshInterval}
 *   onRefresh={() => void refreshDashboard()}
 *   onFullUpdate={() => void updateDashboard()}
 * />
 * ```
 */
export const AutoRefreshButton = memo(function AutoRefreshButton({
  isRefreshing = false,
  isUpdating = false,
  isAutoRefresh,
  onToggleAutoRefresh,
  refreshInterval,
  onSetRefreshInterval,
  onRefresh,
  onFullUpdate,
  scraperSources = [],
  selectedScraperSource,
  onScraperSourceChange,
  className,
}: AutoRefreshButtonProps) {
  const busy = isRefreshing || isUpdating
  const showSourceSelector =
    Boolean(onFullUpdate) && scraperSources.length > 1 && selectedScraperSource && onScraperSourceChange
  const selectedSourceMeta = scraperSources.find((item) => item.id === selectedScraperSource)
  const fullUpdateTitle =
    selectedSourceMeta?.description ?? '从数据源全量采集，通常需要较长时间'

  return (
    <div className={cn('flex flex-wrap items-center gap-2', className)}>
      {/* 轻量刷新 */}
      <button
        type="button"
        onClick={onRefresh}
        disabled={busy}
        title="仅重新拉取看板数据，不触发全量采集"
        className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-3 py-2 text-sm font-medium text-card-foreground transition-colors hover:bg-accent disabled:opacity-50"
      >
        <RefreshCw className={cn('h-4 w-4', isRefreshing && 'animate-spin')} />
        刷新
      </button>

      {/* 全量更新（爬虫） */}
      {onFullUpdate && (
        <>
          {showSourceSelector && (
            <select
              value={selectedScraperSource}
              onChange={(event) => onScraperSourceChange?.(event.target.value)}
              disabled={busy}
              title={selectedSourceMeta?.description}
              aria-label="全量更新数据源"
              className="max-w-[9rem] rounded-xl border border-input bg-background px-2 py-2 text-sm"
            >
              {scraperSources.map((source) => (
                <option key={source.id} value={source.id} title={source.description}>
                  {source.label}
                </option>
              ))}
            </select>
          )}
          <button
            type="button"
            onClick={onFullUpdate}
            disabled={busy}
            title={fullUpdateTitle}
            className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-3 py-2 text-sm font-medium text-card-foreground transition-colors hover:bg-accent disabled:opacity-50"
          >
            <Database className={cn('h-4 w-4', isUpdating && 'animate-pulse')} />
            {isUpdating ? '全量更新中…' : '全量更新'}
          </button>
        </>
      )}

      {/* 自动刷新切换 */}
      <button
        type="button"
        onClick={onToggleAutoRefresh}
        className={cn(
          'inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-sm font-medium transition-colors',
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
            className="rounded-xl border border-input bg-background px-2 py-1 text-sm"
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
