/** 题材四维短线强度仪表 */

import { cn } from '@/lib/utils'

interface ThemeStrengthGaugeProps {
  strengthScore?: number | null
  limitQualityScore?: number | null
  flowScore?: number | null
  leaderClarityScore?: number | null
  breadthScore?: number | null
  className?: string
}

function Bar({ label, value, missing }: { label: string; value: number | null; missing?: boolean }) {
  const pct = missing || value === null ? 0 : Math.max(0, Math.min(100, value))
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{label}</span>
        <span className="tabular-nums text-foreground">
          {missing || value === null ? '暂缺' : value}
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
        <div
          className={cn('h-full rounded-full bg-primary transition-all', missing && 'bg-muted-foreground/30')}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

export function ThemeStrengthGauge({
  strengthScore,
  limitQualityScore,
  flowScore,
  leaderClarityScore,
  breadthScore,
  className,
}: ThemeStrengthGaugeProps) {
  return (
    <div
      data-testid="theme-strength-gauge"
      className={cn('space-y-3 rounded-xl border border-border/70 bg-background/40 p-3', className)}
    >
      <div className="flex items-baseline justify-between">
        <h3 className="text-sm font-semibold text-foreground">短线强度</h3>
        <span className="text-2xl font-bold tabular-nums text-primary">
          {strengthScore ?? '--'}
        </span>
      </div>
      <div className="space-y-2.5">
        <Bar label="涨停质量" value={limitQualityScore ?? null} />
        <Bar label="回流" value={flowScore ?? null} missing={flowScore === null || flowScore === undefined} />
        <Bar label="辨识度龙头" value={leaderClarityScore ?? null} />
        <Bar label="跟风宽度" value={breadthScore ?? null} />
      </div>
    </div>
  )
}
