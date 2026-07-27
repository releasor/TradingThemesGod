/** 近 N 日生命周期与强度轨迹（轻量列表/色带） */

import { useQuery } from '@tanstack/react-query'
import { fetchThemeLifecycle } from '@/api/short-term'
import { ThemeLifecycleBadge } from '@/components/ThemeLifecycleBadge'
import { LoaderCircle } from 'lucide-react'

interface ThemeLifecycleTrendProps {
  themeId: number
  days?: number
}

export function ThemeLifecycleTrend({ themeId, days = 10 }: ThemeLifecycleTrendProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['theme-lifecycle', themeId, days],
    queryFn: () => fetchThemeLifecycle(themeId, days),
    staleTime: 60_000,
  })

  const points = data?.points ?? []
  const maxStrength = Math.max(100, ...points.map((p) => p.strength_score || 0))

  return (
    <div data-testid="theme-lifecycle-trend" className="space-y-3">
      <h3 className="text-sm font-medium text-muted-foreground">近 {days} 日阶段轨迹</h3>
      {isLoading && (
        <div className="flex h-24 items-center justify-center gap-2 text-xs text-muted-foreground">
          <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> 加载轨迹
        </div>
      )}
      {isError && (
        <p className="text-xs text-muted-foreground">轨迹加载失败</p>
      )}
      {!isLoading && !isError && points.length === 0 && (
        <p className="rounded-xl bg-muted/40 px-3 py-4 text-center text-xs text-muted-foreground">
          暂无生命周期快照，请到看板刷新短线信号
        </p>
      )}
      {!isLoading && points.length > 0 && (
        <ul className="space-y-2">
          {[...points].reverse().map((point) => (
            <li
              key={point.trade_date}
              className="flex items-center gap-2 rounded-xl border border-border/50 px-2.5 py-1.5"
            >
              <span className="w-20 shrink-0 text-[11px] tabular-nums text-muted-foreground">
                {point.trade_date.slice(5)}
              </span>
              <ThemeLifecycleBadge stage={point.lifecycle_stage} />
              <div className="min-w-0 flex-1">
                <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${(point.strength_score / maxStrength) * 100}%` }}
                  />
                </div>
              </div>
              <span className="w-8 text-right text-xs font-medium tabular-nums">
                {point.strength_score}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
