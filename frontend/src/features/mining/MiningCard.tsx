import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { ChevronDown, ChevronRight, Loader2 } from 'lucide-react'
import { ensureMiningNote, fetchMiningCard } from '@/api/mining'
import { ThemeLifecycleBadge } from '@/components/ThemeLifecycleBadge'
import { cn } from '@/lib/utils'
import type { LifecycleStage } from '@/types/short-term'
import type { MiningCardItem, MiningMemberItem, MiningNoteResponse } from '@/types/mining'

const LIFECYCLE_STAGES = new Set<string>([
  'germination',
  'fermentation',
  'climax',
  'divergence',
  'ebb',
])

function asLifecycleStage(stage: string): LifecycleStage | null {
  return LIFECYCLE_STAGES.has(stage) ? (stage as LifecycleStage) : null
}

function formatPct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

function noteStatusLabel(status: string): string {
  switch (status) {
    case 'pending':
      return '排队中'
    case 'running':
      return '生成中'
    case 'success':
      return '已完成'
    case 'failed':
      return '失败'
    default:
      return status
  }
}

interface MiningCardProps {
  card: MiningCardItem
  showNoteButton?: boolean
}

export function MiningCard({ card, showNoteButton = false }: MiningCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [members, setMembers] = useState<MiningMemberItem[]>(card.members)
  const [note, setNote] = useState<MiningNoteResponse | null>(card.note)
  const [detailError, setDetailError] = useState(false)

  const noteMutation = useMutation({
    mutationFn: () => ensureMiningNote(card.id),
    onSuccess: (data) => setNote(data),
  })

  const memberPreview = members.length > 0 ? members : []
  const memberCount = card.member_count || memberPreview.length

  const onToggle = async () => {
    const next = !expanded
    setExpanded(next)
    if (!next || members.length > 0) return
    try {
      const detail = await fetchMiningCard(card.id)
      setMembers(detail.members)
      if (detail.note) setNote(detail.note)
      setDetailError(false)
    } catch {
      setDetailError(true)
    }
  }

  return (
    <article
      data-testid={`mining-card-${card.id}`}
      className="rounded-xl border border-border/60 bg-background/60 p-3 sm:p-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 space-y-1">
          <Link
            to={`/themes/${card.theme_id}`}
            className="text-sm font-semibold tracking-tight text-foreground hover:underline"
          >
            {card.theme_name || `题材 #${card.theme_id}`}
          </Link>
          <div className="flex flex-wrap items-center gap-1.5">
            <ThemeLifecycleBadge stage={asLifecycleStage(card.lifecycle_stage)} />
            <span className="text-xs text-muted-foreground">强度 {card.strength_score}</span>
            <span className="rounded-md bg-muted/70 px-1.5 py-0.5 text-[11px] tabular-nums text-muted-foreground">
              分 {card.score}
            </span>
            {card.degraded ? (
              <span className="rounded-md border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 text-[11px] text-amber-700 dark:text-amber-300">
                降级
              </span>
            ) : null}
          </div>
        </div>
      </div>

      {card.rationale ? (
        <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{card.rationale}</p>
      ) : null}

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => void onToggle()}
          className={cn(
            'inline-flex items-center gap-1 rounded-lg border border-border/70 px-2.5 py-1 text-xs font-medium',
            'text-foreground hover:bg-muted/50'
          )}
          aria-expanded={expanded}
        >
          {expanded ? (
            <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
          )}
          展开 · {memberCount}
        </button>

        {showNoteButton ? (
          <button
            type="button"
            onClick={() => noteMutation.mutate()}
            disabled={noteMutation.isPending}
            className="inline-flex items-center gap-1 rounded-lg bg-primary px-2.5 py-1 text-xs font-medium text-primary-foreground disabled:opacity-60"
          >
            {noteMutation.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
            ) : null}
            点评
          </button>
        ) : null}
      </div>

      {note ? (
        <p className="mt-2 text-[11px] text-muted-foreground">
          点评：{noteStatusLabel(note.status)}
          {note.content_md ? ` · ${note.content_md.slice(0, 80)}` : ''}
        </p>
      ) : null}

      {expanded ? (
        <div className="mt-3 space-y-2" data-testid={`mining-card-members-${card.id}`}>
          {detailError ? (
            <p className="text-xs text-destructive">成份股加载失败</p>
          ) : memberPreview.length === 0 ? (
            <p className="text-xs text-muted-foreground">暂无成份股明细</p>
          ) : (
            <ul className="space-y-1.5">
              {memberPreview.map((m) => (
                <li
                  key={m.stock_id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-muted/40 px-2.5 py-1.5 text-xs"
                >
                  <div className="min-w-0">
                    <span className="font-medium tabular-nums">
                      {m.stock_code ?? m.stock_id}
                    </span>
                    {m.stock_name ? (
                      <span className="ml-1.5 text-muted-foreground">{m.stock_name}</span>
                    ) : null}
                    {m.concept_node_name ? (
                      <span className="ml-1.5 rounded border border-border/60 px-1 py-0.5 text-[10px] text-muted-foreground">
                        {m.concept_node_name}
                      </span>
                    ) : null}
                  </div>
                  <div className="flex items-center gap-2 tabular-nums text-muted-foreground">
                    {m.role_tag ? <span>{m.role_tag}</span> : null}
                    <span>分 {m.score}</span>
                    <span>{formatPct(m.rise_fall_pct)}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
          {card.missing_metrics.length > 0 ? (
            <p className="text-[11px] text-amber-700 dark:text-amber-300">
              缺失指标：{card.missing_metrics.join(', ')}
            </p>
          ) : null}
        </div>
      ) : null}
    </article>
  )
}
