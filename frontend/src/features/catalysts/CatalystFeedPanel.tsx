import { cn } from '@/lib/utils'
import type { CatalystFeedItem } from '@/types/catalyst'

const FRESHNESS_LABEL: Record<string, string> = {
  new: '新催化',
  replay: '旧闻',
  unknown: '未知',
}

const ACTOR_LABEL: Record<string, string> = {
  policy: '政策',
  company: '公司',
  other: '其他',
  unknown: '未知',
}

function freshnessClass(value: string): string {
  switch (value) {
    case 'new':
      return 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
    case 'replay':
      return 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300'
    default:
      return 'border-slate-500/30 bg-slate-500/10 text-slate-600 dark:text-slate-300'
  }
}

function actorClass(value: string): string {
  switch (value) {
    case 'policy':
      return 'border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-300'
    case 'company':
      return 'border-violet-500/30 bg-violet-500/10 text-violet-700 dark:text-violet-300'
    case 'other':
      return 'border-orange-500/30 bg-orange-500/10 text-orange-700 dark:text-orange-300'
    default:
      return 'border-slate-500/30 bg-slate-500/10 text-slate-600 dark:text-slate-300'
  }
}

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

function truncate(text: string, max = 120): string {
  const t = text.trim()
  if (t.length <= max) return t
  return `${t.slice(0, max)}…`
}

export interface CatalystFeedFilters {
  freshness: string
  actor: string
  q: string
}

interface CatalystFeedPanelProps {
  items: CatalystFeedItem[]
  filters: CatalystFeedFilters
  selectedThemeId: number | null
  selectedEventId: number | null
  onFiltersChange: (next: Partial<CatalystFeedFilters>) => void
  onSelectEvent: (item: CatalystFeedItem) => void
  loading?: boolean
  error?: boolean
}

export function CatalystFeedPanel({
  items,
  filters,
  selectedThemeId,
  selectedEventId,
  onFiltersChange,
  onSelectEvent,
  loading = false,
  error = false,
}: CatalystFeedPanelProps) {
  return (
    <div className="space-y-4" data-testid="catalyst-feed-panel">
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-muted-foreground">新鲜度</span>
          <select
            value={filters.freshness}
            onChange={(e) => onFiltersChange({ freshness: e.target.value })}
            className="rounded-lg border border-border bg-background px-3 py-1.5"
            aria-label="新鲜度筛选"
          >
            <option value="">全部</option>
            <option value="new">新催化</option>
            <option value="replay">旧闻</option>
            <option value="unknown">未知</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-muted-foreground">主体</span>
          <select
            value={filters.actor}
            onChange={(e) => onFiltersChange({ actor: e.target.value })}
            className="rounded-lg border border-border bg-background px-3 py-1.5"
            aria-label="主体类型筛选"
          >
            <option value="">全部</option>
            <option value="policy">政策</option>
            <option value="company">公司</option>
            <option value="other">其他</option>
            <option value="unknown">未知</option>
          </select>
        </label>
        <label className="flex min-w-[12rem] flex-1 flex-col gap-1 text-sm">
          <span className="text-muted-foreground">关键词</span>
          <input
            type="search"
            value={filters.q}
            onChange={(e) => onFiltersChange({ q: e.target.value })}
            placeholder="标题 / 摘要"
            className="rounded-lg border border-border bg-background px-3 py-1.5"
            aria-label="关键词筛选"
          />
        </label>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">加载催化流…</p>
      ) : error ? (
        <p className="text-sm text-destructive">催化流加载失败</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-muted-foreground" data-testid="catalyst-feed-empty">
          暂无催化事件。可在题材详情刷新洞察后回到本页。
        </p>
      ) : (
        <ul className="space-y-2" data-testid="catalyst-feed-list">
          {items.map((item) => {
            const active =
              selectedEventId === item.event_id ||
              (selectedEventId == null && selectedThemeId === item.theme_id)
            return (
              <li key={item.event_id}>
                <button
                  type="button"
                  onClick={() => onSelectEvent(item)}
                  className={cn(
                    'w-full rounded-lg border px-3 py-3 text-left transition-colors',
                    active
                      ? 'border-primary/40 bg-primary/5'
                      : 'border-border/60 hover:border-border hover:bg-muted/40'
                  )}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={cn(
                        'inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium',
                        freshnessClass(item.freshness)
                      )}
                    >
                      {FRESHNESS_LABEL[item.freshness] ?? item.freshness}
                    </span>
                    <span
                      className={cn(
                        'inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium',
                        actorClass(item.actor_type)
                      )}
                    >
                      {ACTOR_LABEL[item.actor_type] ?? item.actor_type}
                    </span>
                    <span className="text-xs text-muted-foreground">{item.theme_name}</span>
                    <span className="ml-auto text-xs tabular-nums text-muted-foreground">
                      {formatPublishedAt(item.published_at)}
                    </span>
                  </div>
                  <p className="mt-2 text-sm font-medium tracking-tight">{item.title}</p>
                  {item.summary ? (
                    <p className="mt-1 text-xs text-muted-foreground">{truncate(item.summary)}</p>
                  ) : null}
                  <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-muted-foreground">
                    <span>{item.source || '—'}</span>
                    <span>相关 {item.relevance_score}</span>
                  </div>
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
