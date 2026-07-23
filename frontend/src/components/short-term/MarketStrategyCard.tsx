import { Activity, AlertTriangle, Crosshair, Database, Gauge, GitBranch, RefreshCw, Target } from 'lucide-react'
import { cn } from '@/lib/utils'
import { GlowCard } from '@/components/GlowCard'
import type {
  MarketStrategyCardResponse,
  ShortTermPeriod,
  ShortTermPeriodStatus,
  StrategyCardDataSource,
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
  dataSource?: StrategyCardDataSource
  onDataSourceChange?: (source: StrategyCardDataSource) => void
  isLivePreview?: boolean
  degraded?: boolean
  missingSources?: string[]
  isRefreshingData?: boolean
  isAnalyzingDatabase?: boolean
  onRefreshData?: () => void
  onAnalyzeDatabase?: () => void
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
  dataSource = 'database',
  onDataSourceChange,
  isLivePreview = false,
  degraded = false,
  missingSources = [],
  isRefreshingData = false,
  isAnalyzingDatabase = false,
  onRefreshData,
  onAnalyzeDatabase,
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
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Gauge className="h-4 w-4 text-primary" />
            <h2 id="market-strategy-card-heading">{card.title}</h2>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            指数强弱 + 情绪强弱独立择时
            {dateRange ? ` · ${dateRange}` : ''}
            {dataSource === 'live' ? ' · 实时专用数据' : ' · 数据库题材数据'}
          </p>
        </div>
        <div className="flex flex-col items-start gap-2 sm:items-end">
          <div className="flex flex-wrap items-center justify-end gap-1 rounded-xl bg-muted/60 p-1">
            <button
              type="button"
              aria-pressed={dataSource === 'live'}
              onClick={() => onDataSourceChange?.('live')}
              className={cn(
                'rounded-xl px-2 py-1 text-xs font-medium transition-colors',
                dataSource === 'live'
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              实时
            </button>
            <button
              type="button"
              aria-pressed={dataSource === 'database'}
              onClick={() => onDataSourceChange?.('database')}
              className={cn(
                'rounded-xl px-2 py-1 text-xs font-medium transition-colors',
                dataSource === 'database'
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              数据库
            </button>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <button
              type="button"
              title="拉取东方财富指数/情绪题材实时行情，仅更新策略卡专用数据，不影响下方看板"
              onClick={onRefreshData}
              disabled={!onRefreshData || isRefreshingData || isAnalyzingDatabase}
              className="inline-flex h-8 items-center gap-1.5 rounded-xl border border-border bg-background px-2.5 text-xs font-medium text-foreground transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
            >
              <RefreshCw className={cn('h-3.5 w-3.5', isRefreshingData && 'animate-spin')} />
              刷新行情
            </button>
            <button
              type="button"
              title="基于数据库中的题材与快照数据重新计算策略，不访问外部接口"
              onClick={onAnalyzeDatabase}
              disabled={!onAnalyzeDatabase || isRefreshingData || isAnalyzingDatabase}
              className="inline-flex h-8 items-center gap-1.5 rounded-xl border border-border bg-background px-2.5 text-xs font-medium text-foreground transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Database className={cn('h-3.5 w-3.5', isAnalyzingDatabase && 'animate-pulse')} />
              数据库分析
            </button>
          </div>
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

      {isLivePreview && (
        <div className="mt-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">
          当前周期暂无实时数据，以下为数据库预览。请点击「刷新行情」获取实时策略。
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
            主策略          </div>
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
          <ul className="space-y-1 text-xs leading-5 text-muted-foreground">
            {card.rationale.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>

      {(degraded || missingSources.length > 0) && (
        <div className="mt-3 flex items-start gap-2 text-xs text-amber-700 dark:text-amber-300">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>
            数据不完整
            {missingSources.length > 0 ? `：缺失 ${missingSources.join('、')}` : ''}
          </span>
        </div>
      )}

      {periodStatus && (
        <div
          className={cn(
            'mt-3 rounded-xl border px-3 py-2 text-xs font-medium',
            periodStatus.type === 'error'
              ? 'border-destructive/30 bg-destructive/10 text-destructive'
              : periodStatus.type === 'success'
                ? 'border-primary/30 bg-primary/10 text-primary'
                : 'border-border bg-muted/50 text-muted-foreground'
          )}
        >
          {periodStatus.message}
        </div>
      )}
    </section>
    </GlowCard>
  )
}
