import type { ReactNode } from 'react'
import type { ReviewAiReportResponse, ReviewDayResponse } from '@/types/review'
import { ReviewReportPanel } from '@/features/review/ReviewReportPanel'

function Section({
  title,
  children,
  headingId,
}: {
  title: string
  children: ReactNode
  headingId: string
}) {
  return (
    <section className="space-y-3" aria-labelledby={headingId}>
      <h2 id={headingId} className="text-sm font-semibold tracking-tight">
        {title}
      </h2>
      {children}
    </section>
  )
}

function formatPct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

function strategyField(card: Record<string, unknown>, key: string): string | null {
  const value = card[key]
  if (value == null) return null
  if (typeof value === 'string' || typeof value === 'number') return String(value)
  if (Array.isArray(value)) return value.map(String).join('、')
  return null
}

interface ReviewDayPanelProps {
  day: ReviewDayResponse
  reportSeed?: ReviewAiReportResponse | null
  ensurePending?: boolean
}

export function ReviewDayPanel({
  day,
  reportSeed = null,
  ensurePending = false,
}: ReviewDayPanelProps) {
  const strategy = day.strategy_card

  return (
    <div className="space-y-8">
      {day.degraded ? (
        <div
          role="status"
          className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-900 dark:text-amber-100"
          data-testid="review-degraded-banner"
        >
          <p className="font-medium">降级投影：当日无完整事件溯源，已用现有快照回填。</p>
          {day.missing_sources.length > 0 ? (
            <p className="mt-1 text-xs opacity-90">
              缺失源：{day.missing_sources.join('、')}
            </p>
          ) : null}
        </div>
      ) : null}

      <Section title="运行时间线" headingId="review-runs-heading">
        {day.runs.length === 0 ? (
          <p className="text-sm text-muted-foreground">暂无 run 记录</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {day.runs.map((run) => (
              <li
                key={run.id}
                className="flex flex-wrap items-baseline justify-between gap-2 border-b border-border/50 py-2 last:border-0"
              >
                <span>
                  <span className="font-medium">{run.run_type}</span>
                  <span className="ml-2 text-muted-foreground">{run.status}</span>
                </span>
                <span className="text-xs text-muted-foreground">
                  {run.started_at ?? '—'}
                  {run.finished_at ? ` → ${run.finished_at}` : ''}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="策略卡" headingId="review-strategy-heading">
        {!strategy ? (
          <p className="text-sm text-muted-foreground">当日无策略卡结论</p>
        ) : (
          <dl className="grid gap-3 text-sm sm:grid-cols-2">
            {(
              [
                ['title', '标题'],
                ['primary_strategy', '主策略'],
                ['secondary_strategy', '辅策略'],
                ['index_strength', '指数强弱'],
                ['emotion_strength', '情绪强弱'],
                ['operation_advice', '操作建议'],
                ['core_conclusion', '核心结论'],
                ['focus_targets', '关注目标'],
                ['rationale', '依据'],
              ] as const
            ).map(([key, label]) => {
              const text = strategyField(strategy, key)
              if (!text) return null
              return (
                <div key={key} className={key === 'rationale' ? 'sm:col-span-2' : undefined}>
                  <dt className="text-xs text-muted-foreground">{label}</dt>
                  <dd className="mt-0.5">{text}</dd>
                </div>
              )
            })}
          </dl>
        )}
      </Section>

      <Section title="雷达候选" headingId="review-candidates-heading">
        {day.candidates.length === 0 ? (
          <p className="text-sm text-muted-foreground">暂无候选</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[36rem] text-left text-sm">
              <thead className="text-xs text-muted-foreground">
                <tr className="border-b border-border">
                  <th className="py-2 pr-3 font-medium">排名</th>
                  <th className="py-2 pr-3 font-medium">股票</th>
                  <th className="py-2 pr-3 font-medium">题材</th>
                  <th className="py-2 pr-3 font-medium">策略</th>
                  <th className="py-2 pr-3 font-medium">得分</th>
                  <th className="py-2 font-medium">决策</th>
                </tr>
              </thead>
              <tbody>
                {day.candidates.map((c) => (
                  <tr key={`${c.stock_id}-${c.strategy}-${c.rank}`} className="border-b border-border/50">
                    <td className="py-2 pr-3">{c.rank}</td>
                    <td className="py-2 pr-3">
                      {c.stock_name ?? '—'}
                      {c.stock_code ? (
                        <span className="ml-1 text-xs text-muted-foreground">{c.stock_code}</span>
                      ) : null}
                    </td>
                    <td className="py-2 pr-3">{c.theme_name ?? '—'}</td>
                    <td className="py-2 pr-3">{c.strategy}</td>
                    <td className="py-2 pr-3">{c.score}</td>
                    <td className="py-2">{c.decision}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      <Section title="阶段迁移" headingId="review-stages-heading">
        {day.stage_transitions.length === 0 ? (
          <p className="text-sm text-muted-foreground">暂无阶段变化</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {day.stage_transitions.map((t) => (
              <li
                key={`${t.theme_id}-${t.from_stage}-${t.to_stage}`}
                className="flex flex-wrap items-baseline gap-2 border-b border-border/50 py-2 last:border-0"
              >
                <span className="font-medium">{t.theme_name ?? `题材 #${t.theme_id}`}</span>
                <span className="text-muted-foreground">
                  {t.from_stage ?? '—'} → {t.to_stage}
                </span>
                {t.strength_score != null ? (
                  <span className="text-xs text-muted-foreground">强度 {t.strength_score}</span>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="涨跌验证" headingId="review-performance-heading">
        {!day.performance || day.performance.candidates.length === 0 ? (
          <p className="text-sm text-muted-foreground">暂无验证数据</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[28rem] text-left text-sm">
              <thead className="text-xs text-muted-foreground">
                <tr className="border-b border-border">
                  <th className="py-2 pr-3 font-medium">股票</th>
                  <th className="py-2 pr-3 font-medium">当日</th>
                  <th className="py-2 pr-3 font-medium">次日</th>
                  <th className="py-2 font-medium">说明</th>
                </tr>
              </thead>
              <tbody>
                {day.performance.candidates.map((p) => (
                  <tr key={p.stock_id} className="border-b border-border/50">
                    <td className="py-2 pr-3">
                      {p.stock_name ?? '—'}
                      {p.stock_code ? (
                        <span className="ml-1 text-xs text-muted-foreground">{p.stock_code}</span>
                      ) : null}
                    </td>
                    <td className="py-2 pr-3">{formatPct(p.same_day_pct)}</td>
                    <td className="py-2 pr-3">{formatPct(p.next_day_pct)}</td>
                    <td className="py-2 text-muted-foreground">{p.reason ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      <ReviewReportPanel
        tradeDate={day.trade_date}
        seed={reportSeed}
        ensurePending={ensurePending}
      />
    </div>
  )
}
