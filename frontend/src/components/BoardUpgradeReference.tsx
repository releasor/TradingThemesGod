/** 一进二打板候选卡 */

import { memo } from 'react'
import { Crosshair, RefreshCw } from 'lucide-react'
import { cn } from '@/lib/utils'
import { GlowCard } from '@/components/GlowCard'
import type { FirstToSecondCandidateResponse } from '@/types/short-term'

interface BoardUpgradeReferenceProps {
  data?: FirstToSecondCandidateResponse
  isLoading?: boolean
  isRefreshing?: boolean
  onRefresh?: () => void
}

function formatNumber(value: number | null, suffix = '') {
  if (value === null || Number.isNaN(value)) return '--'
  return `${value.toFixed(value >= 100 ? 0 : 1)}${suffix}`
}

function badgeClass(kind: 'match' | 'risk' | 'exclude') {
  if (kind === 'risk') {
    return 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300'
  }
  if (kind === 'exclude') {
    return 'border-destructive/30 bg-destructive/10 text-destructive'
  }
  return 'border-primary/25 bg-primary/10 text-primary'
}

export const BoardUpgradeReference = memo(function BoardUpgradeReference({
  data,
  isLoading = false,
  isRefreshing = false,
  onRefresh,
}: BoardUpgradeReferenceProps) {
  const candidates = data?.candidates ?? []
  return (
    <section
      data-testid="board-upgrade-reference"
      aria-labelledby="board-upgrade-reference-heading"
      className="min-w-0"
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Crosshair className="h-4 w-4 shrink-0 text-primary" />
          <h2 id="board-upgrade-reference-heading" className="text-lg font-semibold text-foreground">
            一进二打板参考
          </h2>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          disabled={isLoading || isRefreshing}
          className="inline-flex h-8 items-center gap-1.5 rounded-xl border border-border bg-background px-2.5 text-xs font-medium text-foreground transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw className={cn('h-3.5 w-3.5', isRefreshing && 'animate-spin')} />
          实时刷新
        </button>
      </div>

      <GlowCard>
      <div className="p-3 text-sm">
        <div className="mb-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span>目标时{data?.trade_date ?? '--'}</span>
          <span>首板时{data?.previous_trade_date ?? '--'}</span>
          <span>排除 {data?.excluded_count ?? 0}</span>
          {data?.degraded && (
            <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-amber-700 dark:text-amber-300">
              数据降级：{data.missing_sources.join('、')}
            </span>
          )}
        </div>

        {isLoading ? (
          <div className="space-y-2">
            <div className="h-20 animate-pulse rounded-xl bg-muted" />
            <div className="h-20 animate-pulse rounded-xl bg-muted" />
          </div>
        ) : candidates.length === 0 ? (
          <div className="rounded-xl bg-muted/40 px-3 py-6 text-center text-sm text-muted-foreground">
            暂无符合条件的一进二候选
          </div>
        ) : (
          <div className="space-y-2">
            {candidates.map((candidate) => (
              <article
                key={candidate.code}
                className="rounded-xl border border-border/70 bg-background/50 p-2.5"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-semibold text-foreground">{candidate.name}</h3>
                      <span className="text-xs text-muted-foreground">{candidate.code}</span>
                      {candidate.theme_name && (
                        <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                          {candidate.theme_name}
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      现价 {formatNumber(candidate.price)} · 流通 {formatNumber(candidate.float_market_cap, '亿')} · 总值 {formatNumber(candidate.market_cap, '亿')} · 换手 {formatNumber(candidate.turnover_rate, '%')}
                    </p>
                  </div>
                  <div className="text-right">
                    <div className="text-xl font-bold text-primary">{candidate.score}</div>
                    <div className="text-[11px] text-muted-foreground">评分</div>
                  </div>
                </div>

                <p className="mt-2 text-xs leading-5 text-card-foreground">
                  {candidate.operation_advice}
                </p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {candidate.matched_rules.slice(0, 4).map((rule) => (
                    <span
                      key={rule}
                      className={cn('rounded-full border px-2 py-0.5 text-[11px]', badgeClass('match'))}
                    >
                      {rule}
                    </span>
                  ))}
                  {candidate.risk_flags.map((rule) => (
                    <span
                      key={rule}
                      className={cn('rounded-full border px-2 py-0.5 text-[11px]', badgeClass('risk'))}
                    >
                      {rule}
                    </span>
                  ))}
                  {candidate.excluded_rules.map((rule) => (
                    <span
                      key={rule}
                      className={cn('rounded-full border px-2 py-0.5 text-[11px]', badgeClass('exclude'))}
                    >
                      {rule}
                    </span>
                  ))}
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
      </GlowCard>
    </section>
  )
})
