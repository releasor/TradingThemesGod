import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { Loader2, Pickaxe } from 'lucide-react'
import { AppCardNav } from '@/components/AppCardNav'
import { GlowCard } from '@/components/GlowCard'
import { ensureMining, fetchMiningBoard } from '@/api/mining'
import { MiningColumn } from '@/features/mining/MiningColumn'
import { useAuthStore } from '@/stores/auth'

function todayIsoDate(): string {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function resolveTradeDate(raw: string | null): string | undefined {
  if (raw && /^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw
  return undefined
}

export function ThemeMiningBoard() {
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const dateParam = resolveTradeDate(searchParams.get('date'))
  const tradeDateInput = dateParam ?? todayIsoDate()
  const token = useAuthStore((s) => s.token)
  const showNoteButton = Boolean(token)

  const boardQuery = useQuery({
    queryKey: ['mining', 'board', dateParam ?? 'latest'],
    queryFn: () =>
      fetchMiningBoard(dateParam ? { trade_date: dateParam } : {}),
  })

  const ensureMutation = useMutation({
    mutationFn: () =>
      ensureMining(dateParam ? { trade_date: dateParam } : {}),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['mining', 'board'] })
    },
  })

  const setDate = (value: string) => {
    const next = new URLSearchParams(searchParams)
    if (value) next.set('date', value)
    else next.delete('date')
    setSearchParams(next, { replace: true })
  }

  const board = boardQuery.data
  const displayDate = board?.trade_date ?? dateParam ?? tradeDateInput

  return (
    <div className="min-h-screen">
      <AppCardNav />
      <main className="mx-auto w-full max-w-none space-y-6 px-3 py-6 sm:px-4 lg:px-5 xl:px-6">
        <GlowCard>
          <section className="space-y-4 p-6 sm:p-8">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <Pickaxe className="h-5 w-5" aria-hidden="true" />
                </div>
                <div>
                  <h1 className="text-xl font-semibold tracking-tight">题材挖掘</h1>
                  <p className="mt-1 text-sm text-muted-foreground">
                    低位分支 · 补涨 · 隐性龙头 — 日快照三列看板
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={() => ensureMutation.mutate()}
                disabled={ensureMutation.isPending}
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground disabled:opacity-60"
              >
                {ensureMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                ) : null}
                重新挖掘
              </button>
            </div>

            <label className="flex flex-wrap items-center gap-2 text-sm">
              <span className="text-muted-foreground">交易日</span>
              <input
                type="date"
                value={tradeDateInput}
                onChange={(e) => setDate(e.target.value)}
                className="rounded-lg border border-border bg-background px-3 py-1.5 tabular-nums"
              />
              {board?.trade_date ? (
                <span className="text-xs text-muted-foreground">当前快照 {displayDate}</span>
              ) : null}
            </label>
          </section>
        </GlowCard>

        {boardQuery.isLoading ? (
          <GlowCard>
            <p className="flex items-center gap-2 p-6 text-sm text-muted-foreground sm:p-8">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              加载题材挖掘…
            </p>
          </GlowCard>
        ) : boardQuery.isError ? (
          <GlowCard>
            <p className="p-6 text-sm text-destructive sm:p-8">题材挖掘加载失败</p>
          </GlowCard>
        ) : (
          <div
            className="grid gap-4 lg:grid-cols-3"
            data-testid="mining-board-columns"
          >
            <MiningColumn
              title="低位分支"
              testId="mining-column-low-branch"
              cards={board?.low_branch ?? []}
              emptyLabel="暂无低位分支候选"
              showNoteButton={showNoteButton}
            />
            <MiningColumn
              title="补涨"
              testId="mining-column-catch-up"
              cards={board?.catch_up ?? []}
              emptyLabel="暂无补涨候选"
              showNoteButton={showNoteButton}
            />
            <MiningColumn
              title="隐性龙头"
              testId="mining-column-hidden-leader"
              cards={board?.hidden_leader ?? []}
              emptyLabel="暂无隐性龙头候选"
              showNoteButton={showNoteButton}
            />
          </div>
        )}
      </main>
    </div>
  )
}
