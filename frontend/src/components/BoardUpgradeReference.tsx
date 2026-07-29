/** 一进二打板候选卡 */

import { memo } from 'react'
import { Crosshair, LoaderCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import AnimatedList from '@/components/AnimatedList'
import { GlowCard } from '@/components/GlowCard'
import type { FirstToSecondCandidateResponse } from '@/types/short-term'

interface BoardUpgradeReferenceProps {
  data?: FirstToSecondCandidateResponse
  isLoading?: boolean
  refreshedAtLabel: string
  isSectionRefreshing?: boolean
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
  refreshedAtLabel,
  isSectionRefreshing = false,
}: BoardUpgradeReferenceProps) {
  const candidates = data?.candidates ?? []
  // 刷新中仍展示上次数据；仅在尚无任何数据时显示骨架
  const showSkeleton = isLoading && candidates.length === 0
  return (
    <section
      data-testid="board-upgrade-reference"
      aria-labelledby="board-upgrade-reference-heading"
      className="min-w-0"
    >
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Crosshair className="h-4 w-4 shrink-0 text-primary" />
        <h2 id="board-upgrade-reference-heading" className="text-lg font-semibold text-foreground">
          一进二打板参考
        </h2>
        <span className="text-xs text-muted-foreground">刷新于 {refreshedAtLabel}</span>
        {isSectionRefreshing && (
          <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
            <LoaderCircle className="h-3 w-3 animate-spin" />
            刷新中…
          </span>
        )}
      </div>

      <GlowCard>
        <div className="px-4 pt-4 text-sm">
          <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span>目标时{data?.trade_date ?? '--'}</span>
            <span>首板时{data?.previous_trade_date ?? '--'}</span>
            <span>排除 {data?.excluded_count ?? 0}</span>
            {data?.degraded && (
              <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-amber-700 dark:text-amber-300">
                数据降级：{data.missing_sources.join('、')}
              </span>
            )}
          </div>
        </div>

        {showSkeleton ? (
          <div className="space-y-2 p-4" data-testid="board-upgrade-skeleton">
            <div className="h-20 animate-pulse rounded-xl bg-muted" />
            <div className="h-20 animate-pulse rounded-xl bg-muted" />
          </div>
        ) : candidates.length === 0 ? (
          <div className="p-4">
            <div className="rounded-xl bg-muted/40 px-3 py-6 text-center text-sm text-muted-foreground">
              暂无符合条件的一进二候选
            </div>
          </div>
        ) : (
          <AnimatedList
            items={candidates}
            getItemKey={(candidate) => candidate.code}
            listTestId="board-upgrade-scroll-container"
            listClassName="!max-h-[520px] xl:!h-auto xl:!max-h-[640px]"
            showGradients
            enableArrowNavigation={false}
            displayScrollbar
            renderItem={(candidate, _index, selected) => (
              <article
                data-testid={`board-upgrade-item-${candidate.code}`}
                className={`item ${selected ? 'selected' : ''}`}
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
                      现价 {formatNumber(candidate.price)} · 流通{' '}
                      {formatNumber(candidate.float_market_cap, '亿')} · 总值{' '}
                      {formatNumber(candidate.market_cap, '亿')} · 换手{' '}
                      {formatNumber(candidate.turnover_rate, '%')}
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
                      className={cn(
                        'rounded-full border px-2 py-0.5 text-[11px]',
                        badgeClass('exclude')
                      )}
                    >
                      {rule}
                    </span>
                  ))}
                </div>
              </article>
            )}
          />
        )}
      </GlowCard>
    </section>
  )
})
