/** 看板刷新进度与当前板块状态 */

import { memo } from 'react'
import { cn } from '@/lib/utils'

export interface DashboardRefreshStatusProps {
  /** 是否正在刷新（轻量或全量） */
  active: boolean
  /** 0–100；null 时仅显示不确定条 */
  progressPct: number | null
  /** 当前正在刷新的板块/阶段 */
  pendingLabel: string | null
  /** 已完成的板块摘要 */
  doneLabels: string[]
  /** 完整状态文案（兼容进度/成功/失败） */
  message: string | null
  messageType?: 'progress' | 'success' | 'error' | 'info' | null
  className?: string
}

export const DashboardRefreshStatus = memo(function DashboardRefreshStatus({
  active,
  progressPct,
  pendingLabel,
  doneLabels,
  message,
  messageType = null,
  className,
}: DashboardRefreshStatusProps) {
  if (!active && !message) return null

  const pct =
    typeof progressPct === 'number' && Number.isFinite(progressPct)
      ? Math.min(100, Math.max(0, Math.round(progressPct)))
      : null

  const tone =
    messageType === 'error'
      ? 'text-destructive'
      : messageType === 'success'
        ? 'text-primary'
        : 'text-muted-foreground'

  return (
    <div
      className={cn(
        'mt-3 rounded-xl border border-border bg-card/80 px-4 py-3 shadow-sm',
        className
      )}
      data-testid="dashboard-refresh-status"
      role="status"
      aria-live="polite"
    >
      {(active || pct !== null) && (
        <div className="mb-2">
          <div className="mb-1.5 flex items-center justify-between gap-3 text-xs">
            <span className="font-medium text-foreground">
              {pendingLabel ? `正在更新：${pendingLabel}` : active ? '刷新进行中' : '刷新进度'}
            </span>
            <span className="tabular-nums text-muted-foreground">
              {pct !== null ? `${pct}%` : '…'}
            </span>
          </div>
          <div
            className="h-2 overflow-hidden rounded-full bg-muted"
            data-testid="dashboard-refresh-status-track"
          >
            <div
              className={cn(
                'h-full rounded-full bg-sky-500 transition-[width] duration-200 ease-out',
                pct === null && 'w-1/3 animate-pulse'
              )}
              style={pct === null ? undefined : { width: `${pct}%` }}
              data-testid="dashboard-refresh-status-bar"
            />
          </div>
        </div>
      )}

      {doneLabels.length > 0 && (
        <p className="mb-1 text-xs text-muted-foreground">
          已完成：{doneLabels.join('；')}
        </p>
      )}

      {message && (
        <p className={cn('text-sm leading-snug', tone)} data-testid="dashboard-refresh-status-message">
          {message}
        </p>
      )}
    </div>
  )
})
