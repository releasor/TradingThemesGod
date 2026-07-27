/** 短线雷达：与下方涨跌幅/行情指标/市场表现同结构的三列分区 */

import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import { LoaderCircle, Radar, RefreshCw } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchShortTermSectors, refreshShortTermSignals } from '@/api/short-term'
import AnimatedList from '@/components/AnimatedList'
import { ThemeLifecycleBadge } from '@/components/ThemeLifecycleBadge'
import { GlowCard } from '@/components/GlowCard'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/auth'
import type {
  SectorRotationItem,
  ShortTermSignalRefreshResponse,
} from '@/types/short-term'

interface ShortTermRadarSectionProps {
  onFeedback?: (type: 'success' | 'error' | 'warning', message: string) => void
  onSelectTheme?: (themeId: number) => void
}

const BOARD_SECTIONS: {
  kind: SectorRotationItem['board_kind']
  title: string
  headingId: string
  empty: string
  limit: number
}[] = [
  {
    kind: 'theme',
    title: '题材轮动',
    headingId: 'radar-theme-heading',
    empty: '暂无题材轮动数据',
    limit: 12,
  },
  {
    kind: 'indicator',
    title: '行情指标',
    headingId: 'radar-indicator-heading',
    empty: '暂无行情指标轮动',
    limit: 12,
  },
  {
    kind: 'market',
    title: '市场表现',
    headingId: 'radar-market-heading',
    empty: '暂无市场表现轮动',
    limit: 12,
  },
]

function formatSignalRefreshSummary(result: ShortTermSignalRefreshResponse): string {
  const updated = [
    `涨停池 ${result.signal_count}`,
    `龙虎榜 ${result.dragon_tiger_count}`,
    `轮动快照 ${result.sector_count}`,
  ]
  const parts = [`已更新：${updated.join(' / ')}（交易日 ${result.trade_date}）`]
  if (result.missing_sources.length > 0) {
    parts.push(`源未完成：${result.missing_sources.join('、')}`)
  }
  return parts.join('。')
}

function SectorCardContent({
  item,
  selected,
}: {
  item: SectorRotationItem
  selected: boolean
}) {
  return (
    <article
      data-testid={`radar-sector-${item.board_kind}-${item.theme_id}`}
      className={cn('item', selected && 'selected')}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h4 className="truncate text-sm font-semibold text-foreground">{item.theme_name}</h4>
          <div className="mt-1 flex flex-wrap items-center gap-1.5">
            <ThemeLifecycleBadge stage={item.lifecycle_stage} />
            <span className="text-[11px] text-muted-foreground">涨停 {item.limit_up_count}</span>
            {item.missing_metrics.includes('flow') && (
              <span className="text-[10px] text-amber-700 dark:text-amber-300">无flow</span>
            )}
          </div>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold text-primary">{item.strength_score}</div>
          <div className="text-[10px] text-muted-foreground">强度</div>
        </div>
      </div>
      {item.summary && (
        <p className="mt-2 line-clamp-2 text-[11px] leading-4 text-muted-foreground">{item.summary}</p>
      )}
    </article>
  )
}

function RadarColumn({
  title,
  headingId,
  empty,
  items,
  limit,
  isLoading,
  onSelect,
}: {
  title: string
  headingId: string
  empty: string
  items: SectorRotationItem[]
  limit: number
  isLoading: boolean
  onSelect?: (themeId: number) => void
}) {
  const shown = items.slice(0, limit)
  return (
    <section className="min-w-0" aria-labelledby={headingId}>
      <div className="mb-4 flex items-baseline justify-between gap-3">
        <h3 id={headingId} className="text-lg font-semibold text-foreground">
          {title}
        </h3>
        {!isLoading && items.length > 0 && (
          <span className="text-xs text-muted-foreground">{items.length} 个板块</span>
        )}
      </div>
      <GlowCard>
        {isLoading && (
          <div className="p-3">
            <div className="h-[320px] animate-pulse rounded-xl bg-muted" />
          </div>
        )}
        {!isLoading && shown.length === 0 && (
          <div className="flex h-[200px] items-center justify-center text-sm text-muted-foreground">
            {empty}
          </div>
        )}
        {!isLoading && shown.length > 0 && (
          <AnimatedList
            items={shown}
            getItemKey={(item) => `${item.board_kind}-${item.theme_id}`}
            listTestId={`radar-${headingId}-scroll`}
            listClassName="!max-h-[420px] xl:!h-auto xl:!max-h-[420px]"
            showGradients
            enableArrowNavigation={false}
            displayScrollbar
            onItemSelect={(item) => onSelect?.(item.theme_id)}
            renderItem={(item, _index, selected) => (
              <SectorCardContent item={item} selected={selected} />
            )}
          />
        )}
      </GlowCard>
    </section>
  )
}

export function ShortTermRadarSection({
  onFeedback,
  onSelectTheme,
}: ShortTermRadarSectionProps) {
  const queryClient = useQueryClient()
  const token = useAuthStore((s) => s.token)
  const navigate = useNavigate()
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastRefreshNote, setLastRefreshNote] = useState<string | null>(null)

  const { data, isLoading, isError, isFetching, refetch } = useQuery({
    queryKey: ['short-term-sectors'],
    queryFn: () => fetchShortTermSectors(),
    staleTime: 30_000,
    placeholderData: keepPreviousData,
  })

  const grouped = useMemo(() => {
    const items = data?.items ?? []
    return {
      theme: items.filter((item) => (item.board_kind ?? 'theme') === 'theme'),
      indicator: items.filter((item) => item.board_kind === 'indicator'),
      market: items.filter((item) => item.board_kind === 'market'),
    }
  }, [data?.items])

  const handleSelect = (themeId: number) => {
    if (onSelectTheme) {
      onSelectTheme(themeId)
      return
    }
    navigate(`/themes/${themeId}`, { state: { from: '/' } })
  }

  const handleRefresh = async () => {
    if (!token) {
      onFeedback?.('warning', '登录后才能刷新短线信号')
      navigate('/login')
      return
    }
    setIsRefreshing(true)
    setLastRefreshNote('正在更新：涨停池 / 龙虎榜 / 轮动快照...')
    try {
      const result = await refreshShortTermSignals()
      await queryClient.invalidateQueries({ queryKey: ['short-term-sectors'] })
      await queryClient.invalidateQueries({ queryKey: ['short-term-overview'] })
      await refetch()
      const summary = formatSignalRefreshSummary(result)
      setLastRefreshNote(summary)
      if (result.status === 'failed') {
        onFeedback?.('error', result.error_message || '短线信号刷新失败')
      } else if (result.degraded) {
        onFeedback?.('warning', summary)
      } else {
        onFeedback?.('success', summary)
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : '刷新失败'
      setLastRefreshNote(`短线信号刷新失败：${message}`)
      onFeedback?.('error', message)
    } finally {
      setIsRefreshing(false)
    }
  }

  const items = data?.items ?? []
  const hasAny = items.length > 0
  const showColumns = !isError || hasAny

  return (
    <section id="short-term-radar" aria-labelledby="short-term-radar-heading" className="mb-6">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <Radar className="h-4 w-4 text-primary" />
          <h2 id="short-term-radar-heading" className="text-lg font-semibold text-foreground">
            短线机会雷达
          </h2>
          {data?.trade_date && (
            <span className="text-xs text-muted-foreground">交易日 {data.trade_date}</span>
          )}
          {(isRefreshing || isFetching) && hasAny && (
            <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
              <LoaderCircle className="h-3 w-3 animate-spin" />
              更新中
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={() => void handleRefresh()}
          disabled={isRefreshing}
          className="inline-flex h-8 items-center gap-1.5 rounded-xl border border-border bg-background px-2.5 text-xs font-medium hover:bg-accent disabled:opacity-50"
        >
          <RefreshCw className={cn('h-3.5 w-3.5', isRefreshing && 'animate-spin')} />
          刷新信号
        </button>
      </div>

      <p className="mb-3 text-xs text-muted-foreground">
        与下方涨跌幅 / 行情指标 / 市场表现同一分类：题材、指标、市场表现各进各列。不构成投资建议。
      </p>
      {lastRefreshNote && <p className="mb-3 text-xs text-primary">{lastRefreshNote}</p>}

      {isError && !hasAny && (
        <div className="mb-4 flex h-24 flex-col items-center justify-center gap-2 rounded-xl border border-border text-sm text-muted-foreground">
          <span>轮动数据加载失败</span>
          <button type="button" className="text-primary hover:underline" onClick={() => void refetch()}>
            重试
          </button>
        </div>
      )}

      {!isLoading && !isError && !hasAny && (
        <div className="rounded-xl border border-border bg-muted/40 px-3 py-6 text-center text-sm text-muted-foreground">
          暂无轮动快照，请登录后点击「刷新信号」
        </div>
      )}

      {showColumns && (isLoading || hasAny) && (
        <div
          className="grid grid-cols-1 gap-6 lg:grid-cols-2 xl:grid-cols-3"
          data-testid="short-term-radar-grid"
        >
          {BOARD_SECTIONS.map((section) => (
            <RadarColumn
              key={section.kind}
              title={section.title}
              headingId={section.headingId}
              empty={section.empty}
              items={grouped[section.kind]}
              limit={section.limit}
              isLoading={isLoading && !hasAny}
              onSelect={handleSelect}
            />
          ))}
        </div>
      )}
    </section>
  )
}
