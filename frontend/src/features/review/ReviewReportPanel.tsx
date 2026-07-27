import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { fetchReviewReport } from '@/api/review'
import type { ReviewAiReportResponse } from '@/types/review'

const TERMINAL_STATUSES = new Set(['success', 'failed', 'rule_fallback'])

function statusLabel(status: string): string {
  switch (status) {
    case 'pending':
      return '排队中'
    case 'running':
      return '生成中'
    case 'success':
      return '已完成'
    case 'rule_fallback':
      return '规则摘要'
    case 'failed':
      return '生成失败'
    default:
      return status
  }
}

interface ReviewReportPanelProps {
  tradeDate: string
  /** Seed from ensure mutation; query keeps polling when pending/running */
  seed?: ReviewAiReportResponse | null
  ensurePending?: boolean
}

export function ReviewReportPanel({
  tradeDate,
  seed = null,
  ensurePending = false,
}: ReviewReportPanelProps) {
  const reportQuery = useQuery({
    queryKey: ['review', 'report', tradeDate],
    queryFn: () => fetchReviewReport(tradeDate),
    // ensure 完成前不主动 GET，避免尚无日报时的空请求
    enabled: Boolean(tradeDate) && !ensurePending,
    initialData: seed ?? undefined,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status === 'pending' || status === 'running') return 2000
      return false
    },
  })

  const report = reportQuery.data ?? seed
  const isBusy =
    ensurePending ||
    report?.status === 'pending' ||
    report?.status === 'running' ||
    reportQuery.isFetching

  return (
    <section className="space-y-3" aria-labelledby="review-report-heading">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="review-report-heading" className="text-sm font-semibold tracking-tight">
          AI 题材日报
        </h2>
        {report ? (
          <span className="text-xs text-muted-foreground">
            {statusLabel(report.status)}
            {report.model_name ? ` · ${report.model_name}` : ''}
          </span>
        ) : null}
      </div>

      {ensurePending && !report ? (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          正在确保日报…
        </p>
      ) : null}

      {!ensurePending && !report && !reportQuery.isFetching ? (
        <p className="text-sm text-muted-foreground">暂无日报</p>
      ) : null}

      {report ? (
        <div className="space-y-3">
          {(report.status === 'pending' || report.status === 'running') && (
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              日报{statusLabel(report.status)}，约每 2 秒刷新…
            </p>
          )}
          {report.error ? (
            <p className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              {report.error}
            </p>
          ) : null}
          {report.content_md ? (
            <div className="whitespace-pre-wrap text-sm leading-relaxed text-foreground/90">
              {report.content_md}
            </div>
          ) : (
            !TERMINAL_STATUSES.has(report.status) && (
              <p className="text-sm text-muted-foreground">等待内容…</p>
            )
          )}
          {isBusy && report.content_md ? (
            <span className="sr-only">日报仍在刷新</span>
          ) : null}
        </div>
      ) : null}
    </section>
  )
}
