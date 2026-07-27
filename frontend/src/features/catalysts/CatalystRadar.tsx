import { useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { Radar, Loader2 } from 'lucide-react'
import { AppCardNav } from '@/components/AppCardNav'
import { GlowCard } from '@/components/GlowCard'
import {
  ensureCatalystClassify,
  fetchCatalystFeed,
  fetchCatalystThemeSummary,
} from '@/api/catalysts'
import type { CatalystFeedItem } from '@/types/catalyst'
import {
  CatalystFeedPanel,
  type CatalystFeedFilters,
} from '@/features/catalysts/CatalystFeedPanel'
import { CatalystThemeSummary } from '@/features/catalysts/CatalystThemeSummary'

function parseThemeId(raw: string | null): number | null {
  if (!raw) return null
  const n = Number(raw)
  if (!Number.isFinite(n) || n <= 0 || !Number.isInteger(n)) return null
  return n
}

function debounceKey(q: string): string {
  return q.trim()
}

export function CatalystRadar() {
  const [searchParams, setSearchParams] = useSearchParams()
  const themeId = parseThemeId(searchParams.get('themeId'))
  const freshness = searchParams.get('freshness') ?? ''
  const actor = searchParams.get('actor') ?? ''

  const [qInput, setQInput] = useState(searchParams.get('q') ?? '')
  const [debouncedQ, setDebouncedQ] = useState(debounceKey(searchParams.get('q') ?? ''))
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null)
  const ensuredRef = useRef(false)

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setDebouncedQ(debounceKey(qInput))
    }, 250)
    return () => window.clearTimeout(handle)
  }, [qInput])

  useEffect(() => {
    const current = searchParams.get('q') ?? ''
    if (debouncedQ === current) return
    const next = new URLSearchParams(searchParams)
    if (debouncedQ) next.set('q', debouncedQ)
    else next.delete('q')
    setSearchParams(next, { replace: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps -- sync q into URL only
  }, [debouncedQ])

  const ensureMutation = useMutation({
    mutationFn: () => ensureCatalystClassify({ use_model: false }),
  })

  useEffect(() => {
    if (ensuredRef.current) return
    ensuredRef.current = true
    ensureMutation.mutate()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- once on mount
  }, [])

  const feedQuery = useQuery({
    queryKey: ['catalysts', 'feed', freshness, actor, themeId, debouncedQ],
    queryFn: () =>
      fetchCatalystFeed({
        ...(freshness ? { freshness } : {}),
        ...(actor ? { actor_type: actor } : {}),
        ...(themeId != null ? { theme_id: themeId } : {}),
        ...(debouncedQ ? { q: debouncedQ } : {}),
      }),
  })

  const summaryQuery = useQuery({
    queryKey: ['catalysts', 'summary', themeId],
    queryFn: () => fetchCatalystThemeSummary(themeId!),
    enabled: themeId != null,
  })

  const patchParams = (patch: Record<string, string | null>) => {
    const next = new URLSearchParams(searchParams)
    for (const [key, value] of Object.entries(patch)) {
      if (value == null || value === '') next.delete(key)
      else next.set(key, value)
    }
    setSearchParams(next, { replace: true })
  }

  const onFiltersChange = (next: Partial<CatalystFeedFilters>) => {
    if (next.q !== undefined) {
      setQInput(next.q)
      return
    }
    patchParams({
      ...(next.freshness !== undefined ? { freshness: next.freshness || null } : {}),
      ...(next.actor !== undefined ? { actor: next.actor || null } : {}),
    })
  }

  const onSelectEvent = (item: CatalystFeedItem) => {
    setSelectedEventId(item.event_id)
    patchParams({ themeId: String(item.theme_id) })
  }

  const filters: CatalystFeedFilters = useMemo(
    () => ({ freshness, actor, q: qInput }),
    [freshness, actor, qInput]
  )

  return (
    <div className="min-h-screen">
      <AppCardNav />
      <main className="mx-auto w-full max-w-none space-y-6 px-3 py-6 sm:px-4 lg:px-5 xl:px-6">
        <GlowCard>
          <section className="space-y-2 p-6 sm:p-8">
            <div className="flex flex-wrap items-start gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Radar className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <h1 className="text-xl font-semibold tracking-tight">催化雷达</h1>
                <p className="mt-1 text-sm text-muted-foreground">
                  跨题材驱动事件流：区分新催化与旧闻，政策与公司主体
                </p>
              </div>
            </div>
          </section>
        </GlowCard>

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
          <GlowCard>
            <div className="p-6 sm:p-8">
              <div className="mb-4 flex items-center justify-between gap-2">
                <h2 className="text-sm font-semibold tracking-tight">事件时间流</h2>
                {feedQuery.isFetching ? (
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" aria-hidden="true" />
                ) : null}
              </div>
              <CatalystFeedPanel
                items={feedQuery.data?.items ?? []}
                filters={filters}
                selectedThemeId={themeId}
                selectedEventId={selectedEventId}
                onFiltersChange={onFiltersChange}
                onSelectEvent={onSelectEvent}
                loading={feedQuery.isLoading}
                error={feedQuery.isError}
              />
            </div>
          </GlowCard>

          <GlowCard>
            <div className="p-6 sm:p-8">
              <div className="mb-4 flex items-center justify-between gap-2">
                <h2 className="text-sm font-semibold tracking-tight">题材摘要</h2>
                {summaryQuery.isFetching ? (
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" aria-hidden="true" />
                ) : null}
              </div>
              <CatalystThemeSummary
                summary={themeId != null ? (summaryQuery.data ?? null) : null}
                loading={themeId != null && summaryQuery.isLoading}
                error={themeId != null && summaryQuery.isError}
              />
            </div>
          </GlowCard>
        </div>
      </main>
    </div>
  )
}
