import type { ThemeBrief } from '@/types/theme'
import { ThemeRiseFallBar } from '@/components/charts/ThemeRiseFallBar'
import { GlowCard } from '@/components/GlowCard'

interface MarketSignalSectionProps {
  signals: ThemeBrief[]
  isLoading?: boolean
  isError?: boolean
  onSelect: (themeId: number) => void
  title?: string
  headingId?: string
  emptyText?: string
  errorText?: string
  testIdPrefix?: string
}

export function MarketSignalSection({
  signals,
  isLoading = false,
  isError = false,
  onSelect,
  title = '市场表现',
  headingId = 'market-signal-heading',
  emptyText = '暂无市场表现数据',
  errorText = '市场表现加载失败',
  testIdPrefix = 'market-signal',
}: MarketSignalSectionProps) {
  return (
    <section className="min-w-0" aria-labelledby={headingId}>
      <div className="mb-4 flex items-baseline justify-between gap-3">
        <h2 id={headingId} className="text-lg font-semibold text-foreground">
          {title}
        </h2>
        {!isLoading && !isError && signals.length > 0 && (
          <span className="text-xs text-muted-foreground">{signals.length} 个板块</span>
        )}
      </div>

      <GlowCard>
      <div className="p-3">
        {isLoading && (
          <div
            data-testid={`${testIdPrefix}-skeleton`}
            className="h-[380px] animate-pulse rounded-xl bg-muted"
          />
        )}

        {!isLoading && isError && signals.length === 0 && (
          <div className="flex h-[380px] items-center justify-center text-sm text-destructive">
            {errorText}
          </div>
        )}

        {!isLoading && !isError && signals.length === 0 && (
          <div className="flex h-[380px] items-center justify-center text-sm text-muted-foreground">
            {emptyText}
          </div>
        )}

        {!isLoading && signals.length > 0 && (
          <ThemeRiseFallBar themes={signals} onThemeClick={onSelect} />
        )}
      </div>
      </GlowCard>
    </section>
  )
}
