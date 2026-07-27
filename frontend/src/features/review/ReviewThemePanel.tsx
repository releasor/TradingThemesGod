import type { ReviewThemeResponse } from '@/types/review'

interface ReviewThemePanelProps {
  theme: ReviewThemeResponse
  onSelectDate: (date: string) => void
}

function formatPct(value: number | null): string {
  if (value == null || Number.isNaN(value)) return '—'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

export function ReviewThemePanel({ theme, onSelectDate }: ReviewThemePanelProps) {
  return (
    <div className="space-y-8">
      <header className="space-y-1">
        <h2 className="text-base font-semibold tracking-tight">{theme.theme_name}</h2>
        <p className="text-sm text-muted-foreground">近 {theme.days} 日轨迹 · 题材 #{theme.theme_id}</p>
      </header>

      <section className="space-y-3" aria-labelledby="review-trajectory-heading">
        <h3 id="review-trajectory-heading" className="text-sm font-semibold tracking-tight">
          阶段轨迹
        </h3>
        {theme.trajectory.length === 0 ? (
          <p className="text-sm text-muted-foreground">暂无轨迹</p>
        ) : (
          <ul className="space-y-2">
            {theme.trajectory.map((point) => (
              <li key={point.trade_date}>
                <button
                  type="button"
                  onClick={() => onSelectDate(point.trade_date)}
                  className="flex w-full flex-wrap items-baseline justify-between gap-2 rounded-lg border border-transparent px-2 py-2 text-left text-sm transition-colors hover:border-border hover:bg-muted/40"
                >
                  <span className="font-medium tabular-nums">{point.trade_date}</span>
                  <span className="text-muted-foreground">{point.stage}</span>
                  <span className="text-xs text-muted-foreground">强度 {point.strength_score}</span>
                  <span className="text-xs tabular-nums">{formatPct(point.rise_fall_pct)}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-3" aria-labelledby="review-related-candidates-heading">
        <h3 id="review-related-candidates-heading" className="text-sm font-semibold tracking-tight">
          关联候选
        </h3>
        {theme.related_candidates.length === 0 ? (
          <p className="text-sm text-muted-foreground">窗口内无候选命中</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {theme.related_candidates.map((c) => (
              <li
                key={`${c.stock_id}-${c.strategy}-${c.rank}`}
                className="flex flex-wrap items-baseline gap-2 border-b border-border/50 py-2 last:border-0"
              >
                <span className="font-medium">
                  {c.stock_name ?? '—'}
                  {c.stock_code ? (
                    <span className="ml-1 text-xs font-normal text-muted-foreground">
                      {c.stock_code}
                    </span>
                  ) : null}
                </span>
                <span className="text-muted-foreground">{c.strategy}</span>
                <span className="text-xs text-muted-foreground">
                  得分 {c.score} · {c.decision}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
