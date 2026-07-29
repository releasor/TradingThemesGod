/** 短线雷达：与下方涨跌幅/行情指标/市场表现同结构的三列分区 */

import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { LoaderCircle, Radar } from 'lucide-react'
import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchShortTermSectors } from '@/api/short-term'
import AnimatedList from '@/components/AnimatedList'
import { ThemeLifecycleBadge } from '@/components/ThemeLifecycleBadge'
import { GlowCard } from '@/components/GlowCard'
import { cn } from '@/lib/utils'
import type { SectorRotationItem } from '@/types/short-term'

interface ShortTermRadarSectionProps {
  refreshedAtLabel: string
  isSectionRefreshing?: boolean
  onSelectTheme?: (themeId: number) => void
  /** 看板活跃题材源；轮动快照按 Theme.source 过滤 */
  source?: string
  sourceLabel?: string
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
  refreshedAtLabel,
  isSectionRefreshing = false,
  onSelectTheme,
  source,
  sourceLabel,
}: ShortTermRadarSectionProps) {
  const navigate = useNavigate()

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['short-term-sectors', source ?? 'eastmoney'],
    queryFn: ({ signal }) => fetchShortTermSectors(undefined, signal, source),
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

  const items = data?.items ?? []
  const hasAny = items.length > 0
  const showColumns = !isError || hasAny
  const sourceSuffix = sourceLabel ? ` · ${sourceLabel}` : ''

  return (
    <section id="short-term-radar" aria-labelledby="short-term-radar-heading" className="mb-6">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Radar className="h-4 w-4 text-primary" />
        <h2 id="short-term-radar-heading" className="text-lg font-semibold text-foreground">
          短线机会雷达{sourceSuffix}
        </h2>
        <span className="text-xs text-muted-foreground">刷新于 {refreshedAtLabel}</span>
        {data?.trade_date && (
          <span className="text-xs text-muted-foreground">交易日 {data.trade_date}</span>
        )}
        {(isSectionRefreshing || isFetching) && (
          <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
            <LoaderCircle className="h-3 w-3 animate-spin" />
            刷新中…
          </span>
        )}
      </div>

      <p className="mb-3 text-xs text-muted-foreground">
        按当前题材源过滤轮动快照；与下方涨跌幅 / 行情指标 / 市场表现同一分类。若该源暂无快照，请用顶部「刷新」重建短线信号。不构成投资建议。
      </p>

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
          {sourceLabel
            ? `${sourceLabel} 暂无轮动快照。请切换回已有快照的源，或点击顶部「刷新」按各源题材重建雷达。`
            : '暂无轮动快照，请使用顶部刷新'}
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
