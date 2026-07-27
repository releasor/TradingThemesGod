import { Link } from 'react-router-dom'
import { ThemeLifecycleBadge } from '@/components/ThemeLifecycleBadge'
import type { CatalystThemeSummaryResponse } from '@/types/catalyst'
import type { LifecycleStage } from '@/types/short-term'

const LIFECYCLE_STAGES = new Set<string>([
  'germination',
  'fermentation',
  'climax',
  'divergence',
  'ebb',
])

const COUNT_LABELS: { key: string; label: string }[] = [
  { key: 'new', label: '新催化' },
  { key: 'replay', label: '旧闻' },
  { key: 'policy', label: '政策' },
  { key: 'company', label: '公司' },
  { key: 'other', label: '其他' },
]

function formatPublishedAt(value: string): string {
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

interface CatalystThemeSummaryProps {
  summary: CatalystThemeSummaryResponse | null
  loading?: boolean
  error?: boolean
  emptyHint?: string
}

export function CatalystThemeSummary({
  summary,
  loading = false,
  error = false,
  emptyHint = '点击左侧事件查看题材摘要',
}: CatalystThemeSummaryProps) {
  if (loading) {
    return <p className="text-sm text-muted-foreground">加载题材摘要…</p>
  }
  if (error) {
    return <p className="text-sm text-destructive">题材摘要加载失败</p>
  }
  if (!summary) {
    return (
      <p className="text-sm text-muted-foreground" data-testid="catalyst-summary-empty">
        {emptyHint}
      </p>
    )
  }

  const stage =
    summary.lifecycle_stage && LIFECYCLE_STAGES.has(summary.lifecycle_stage)
      ? (summary.lifecycle_stage as LifecycleStage)
      : null

  return (
    <div className="space-y-6" data-testid="catalyst-theme-summary">
      <header className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-base font-semibold tracking-tight">{summary.theme_name}</h2>
          {stage ? <ThemeLifecycleBadge stage={stage} /> : null}
        </div>
        <p className="text-sm text-muted-foreground">
          <Link
            to={`/themes/${summary.theme_id}`}
            className="text-primary underline-offset-2 hover:underline"
          >
            打开题材详情
          </Link>
          {summary.strength_score != null ? (
            <span className="ml-2">强度 {summary.strength_score}</span>
          ) : null}
        </p>
      </header>

      <section className="space-y-2" aria-labelledby="catalyst-counts-heading">
        <h3 id="catalyst-counts-heading" className="text-sm font-semibold tracking-tight">
          近 7 日计数
        </h3>
        <dl className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
          {COUNT_LABELS.map(({ key, label }) => (
            <div key={key} className="rounded-lg border border-border/60 px-3 py-2">
              <dt className="text-xs text-muted-foreground">{label}</dt>
              <dd className="mt-0.5 tabular-nums font-medium">{summary.counts[key] ?? 0}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="space-y-2" aria-labelledby="catalyst-recent-heading">
        <h3 id="catalyst-recent-heading" className="text-sm font-semibold tracking-tight">
          最近驱动事件
        </h3>
        {summary.recent_events.length === 0 ? (
          <p className="text-sm text-muted-foreground">暂无驱动事件</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {summary.recent_events.map((ev) => (
              <li
                key={ev.event_id}
                className="border-b border-border/50 py-2 last:border-0"
              >
                <p className="font-medium">{ev.title}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {formatPublishedAt(ev.published_at)} · {ev.source || '—'}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-2" aria-labelledby="catalyst-news-heading">
        <h3 id="catalyst-news-heading" className="text-sm font-semibold tracking-tight">
          相关新闻标题
        </h3>
        {summary.news_headlines.length === 0 ? (
          <p className="text-sm text-muted-foreground">暂无关键词匹配新闻</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {summary.news_headlines.map((news, idx) => (
              <li key={`${news.url}-${idx}`} className="border-b border-border/50 py-2 last:border-0">
                {news.url ? (
                  <a
                    href={news.url}
                    target="_blank"
                    rel="noreferrer"
                    className="font-medium text-primary underline-offset-2 hover:underline"
                  >
                    {news.title}
                  </a>
                ) : (
                  <p className="font-medium">{news.title}</p>
                )}
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {formatPublishedAt(news.published_at)}
                  {news.match_note ? ` · ${news.match_note}` : ''}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
