import { Activity, AlertTriangle, Crosshair, Gauge, GitBranch, Target } from 'lucide-react'
import { cn } from '@/lib/utils'
import { GlowCard } from '@/components/GlowCard'
import type {
  MarketStrategyCardResponse,
  ShortTermPeriod,
  ShortTermPeriodStatus,
} from '@/types/short-term'

interface MarketStrategyCardProps {
  card: MarketStrategyCardResponse
  period?: ShortTermPeriod
  periodLabel?: string
  dateRange?: string
  onPeriodChange?: (period: ShortTermPeriod) => void
  customStartDate?: string
  customEndDate?: string
  onCustomDateRangeChange?: (startDate: string, endDate: string) => void
  periodStatus?: ShortTermPeriodStatus | null
  isPeriodLoading?: boolean
  isPreview?: boolean
  degraded?: boolean
  missingSources?: string[]
  refreshedAtLabel?: string
}

const PERIOD_OPTIONS: Array<{ value: ShortTermPeriod; label: string }> = [
  { value: 'today', label: '当日' },
  { value: 'current_week', label: '本周' },
  { value: 'half_month', label: '近半月' },
  { value: 'current_month', label: '本月' },
  { value: 'custom', label: '自定义' },
]

function strengthText(value: MarketStrategyCardResponse['index_strength']) {
  return value === 'strong' ? '强' : '弱'
}

function strengthClass(value: MarketStrategyCardResponse['index_strength']) {
  return value === 'strong'
    ? 'border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-300'
    : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
}

export function MarketStrategyCard({
  card,
  period = 'today',
  periodLabel,
  dateRange,
  onPeriodChange,
  customStartDate,
  customEndDate,
  onCustomDateRangeChange,
  periodStatus,
  isPeriodLoading = false,
  isPreview = false,
  degraded = false,
  missingSources = [],
  refreshedAtLabel,
}: MarketStrategyCardProps) {
  return (
    <GlowCard>
      <section
        aria-labelledby="market-strategy-card-heading"
        aria-label={periodLabel ? `当前周期：${periodLabel}` : undefined}
        className="p-3 text-card-foreground sm:p-4"
        data-testid="market-strategy-card"
      >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2 text-sm font-semibold">
            <Gauge className="h-4 w-4 text-primary" />
            <h2 id="market-strategy-card-heading">{card.title}</h2>
            {refreshedAtLabel != null && (
              <span className="text-xs font-normal text-muted-foreground">
                刷新于 {refreshedAtLabel}
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            指数强弱 + 情绪强弱独立择时
            {dateRange ? ` · ${dateRange}` : ''}
          </p>
        </div>
        <div className="flex flex-col items-start gap-2 sm:items-end">
          <div className="flex flex-wrap items-center gap-1 rounded-xl bg-muted/60 p-1">
            {PERIOD_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                aria-pressed={period === option.value}
                onClick={() => onPeriodChange?.(option.value)}
                className={cn(
                  'rounded-xl px-2 py-1 text-xs font-medium transition-colors',
                  period === option.value
                    ? 'bg-background text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
          {period === 'custom' && (
            <div className="flex flex-wrap items-center justify-end gap-2">
              <input
                type="date"
                aria-label="自定义开始日期"
                value={customStartDate ?? ''}
                onChange={(event) =>
                  onCustomDateRangeChange?.(event.target.value, customEndDate ?? '')
                }
                className="h-8 rounded-xl border border-border bg-background px-2 text-xs text-foreground"
              />
              <span className="text-xs text-muted-foreground">至</span>
              <input
                type="date"
                aria-label="自定义结束日期"
                value={customEndDate ?? ''}
                onChange={(event) =>
                  onCustomDateRangeChange?.(customStartDate ?? '', event.target.value)
                }
                className="h-8 rounded-xl border border-border bg-background px-2 text-xs text-foreground"
              />
            </div>
          )}
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={cn(
                'rounded-full border px-2 py-0.5 text-xs font-medium',
                strengthClass(card.index_strength)
              )}
            >
              指数{strengthText(card.index_strength)}
            </span>
            <span
              className={cn(
                'rounded-full border px-2 py-0.5 text-xs font-medium',
                strengthClass(card.emotion_strength)
              )}
            >
              情绪{strengthText(card.emotion_strength)}
            </span>
            {degraded && (
              <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-xs font-medium text-amber-700 dark:text-amber-300">
                数据降级
              </span>
            )}
          </div>
        </div>
      </div>

      {isPreview && (
        <div className="mt-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">
          当前为缓存预览。请点击顶部「刷新」获取最新策略。
        </div>
      )}

      <div
        className={cn(
          'mt-3 grid gap-3 md:grid-cols-2 transition-opacity',
          isPeriodLoading && 'pointer-events-none opacity-50'
        )}
      >
        <div className="rounded-xl bg-muted/40 p-3">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Target className="h-3.5 w-3.5" />
            主策略
          </div>
          <p className="mt-1 text-base font-semibold text-foreground">{card.primary_strategy}</p>
        </div>
        <div className="rounded-xl bg-muted/40 p-3">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <GitBranch className="h-3.5 w-3.5" />
            节奏策略
          </div>
          <p className="mt-1 text-base font-semibold text-foreground">{card.secondary_strategy}</p>
        </div>
      </div>

      <div
        className={cn(
          'mt-3 flex items-start gap-2 rounded-xl border border-border/70 bg-background/50 p-3 text-sm transition-opacity',
          isPeriodLoading && 'opacity-50'
        )}
      >
        <Crosshair className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
        <p className="leading-6">{card.operation_advice}</p>
      </div>

      <div
        className={cn(
          'mt-3 grid gap-3 lg:grid-cols-[1fr_1.2fr] transition-opacity',
          isPeriodLoading && 'opacity-50'
        )}
      >
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-medium text-muted-foreground">
            <Activity className="h-3.5 w-3.5" />
            重点跟踪
          </div>
          <div className="flex flex-wrap gap-2">
            {card.focus_targets.map((target) => (
              <span
                key={target}
                className="rounded-full bg-primary/10 px-2 py-1 text-xs font-medium text-primary"
              >
                {target}
              </span>
            ))}
          </div>
        </div>

        <div>
          <div className="mb-2 text-xs font-medium text-muted-foreground">判断依据</div>
          <ul className="space-y-2 text-xs leading-5 text-muted-foreground">
            {card.rationale.map((item, index) => (
              <li
                key={item}
                className="grid gap-2 rounded-lg border border-border/50 bg-muted/20 px-2.5 py-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]"
                data-testid={`strategy-rationale-${index}`}
              >
                <span className="text-foreground/90">{item}</span>
                <span
                  className="border-t border-border/40 pt-1.5 text-[11px] leading-4 text-muted-foreground sm:border-l sm:border-t-0 sm:pl-2.5 sm:pt-0"
                  data-testid={`strategy-formula-${index}`}
                >
                  {card.formulas?.[index] ?? '计算公式待补充'}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {missingSources.length > 0 && (
        <div className="mt-3 flex items-start gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <p>部分数据源缺失：{missingSources.join('、')}</p>
        </div>
      )}

      {periodStatus && (
        <p
          className={cn(
            'mt-3 text-xs',
            periodStatus.type === 'error'
              ? 'text-destructive'
              : periodStatus.type === 'success'
                ? 'text-primary'
                : 'text-muted-foreground'
          )}
        >
          {periodStatus.message}
        </p>
      )}
      </section>
    </GlowCard>
  )
}
