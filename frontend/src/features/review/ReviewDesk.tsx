import { useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { BookOpen, Loader2 } from 'lucide-react'
import { AppCardNav } from '@/components/AppCardNav'
import { GlowCard } from '@/components/GlowCard'
import { cn } from '@/lib/utils'
import {
  ensureReviewReport,
  fetchReviewDay,
  fetchReviewTheme,
} from '@/api/review'
import { resolveTradeDate as resolveTradeDateApi } from '@/api/trading-calendar'
import type { ReviewAiReportResponse } from '@/types/review'
import { ReviewDayPanel } from '@/features/review/ReviewDayPanel'
import { ReviewThemePanel } from '@/features/review/ReviewThemePanel'

type ReviewMode = 'day' | 'theme'

/** 本地周末回退（API 未返回前的即时兜底） */
export function resolveTradeDateIso(iso?: string | null): string {
  const now = iso && /^\d{4}-\d{2}-\d{2}$/.test(iso) ? parseLocalDate(iso) : new Date()
  const day = now.getDay()
  if (day === 0) now.setDate(now.getDate() - 2)
  else if (day === 6) now.setDate(now.getDate() - 1)
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function parseLocalDate(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}

function parseThemeId(raw: string | null): number | null {
  if (!raw) return null
  const n = Number(raw)
  if (!Number.isFinite(n) || n <= 0 || !Number.isInteger(n)) return null
  return n
}

export function ReviewDesk() {
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const dateParam = searchParams.get('date')
  const themeIdParam = searchParams.get('themeId')

  const mode: ReviewMode = themeIdParam ? 'theme' : 'day'
  const localTradeDate = resolveTradeDateIso(
    dateParam && /^\d{4}-\d{2}-\d{2}$/.test(dateParam) ? dateParam : null
  )
  const themeId = parseThemeId(themeIdParam)

  const [themeIdInput, setThemeIdInput] = useState(themeIdParam ?? '')
  const [reportSeed, setReportSeed] = useState<ReviewAiReportResponse | null>(null)
  const ensuredDateRef = useRef<string | null>(null)

  const resolveQuery = useQuery({
    queryKey: [
      'market',
      'calendar',
      'resolve',
      dateParam && /^\d{4}-\d{2}-\d{2}$/.test(dateParam) ? dateParam : 'today',
    ],
    queryFn: () =>
      resolveTradeDateApi(
        dateParam && /^\d{4}-\d{2}-\d{2}$/.test(dateParam) ? dateParam : undefined
      ),
    staleTime: 5 * 60_000,
  })

  const tradeDate = resolveQuery.data?.trade_date ?? localTradeDate

  useEffect(() => {
    setThemeIdInput(themeIdParam ?? '')
  }, [themeIdParam])

  useEffect(() => {
    setReportSeed(null)
    ensuredDateRef.current = null
  }, [tradeDate])

  // URL 规范化为服务端解析后的交易日
  useEffect(() => {
    if (mode !== 'day') return
    if (!resolveQuery.data?.trade_date) return
    if (dateParam === resolveQuery.data.trade_date) return
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('date', resolveQuery.data.trade_date)
    setSearchParams(nextParams, { replace: true })
  }, [mode, resolveQuery.data?.trade_date, dateParam, searchParams, setSearchParams])

  const dayQuery = useQuery({
    queryKey: ['review', 'day', tradeDate],
    queryFn: () => fetchReviewDay(tradeDate),
    enabled: mode === 'day',
  })

  const themeQuery = useQuery({
    queryKey: ['review', 'theme', themeId],
    queryFn: () => fetchReviewTheme(themeId!),
    enabled: mode === 'theme' && themeId != null,
  })

  // 后端若再解析出不同交易日，同步到 URL
  useEffect(() => {
    if (mode !== 'day') return
    const resolved = dayQuery.data?.trade_date
    if (!resolved || resolved === tradeDate) return
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('date', resolved)
    setSearchParams(nextParams, { replace: true })
  }, [mode, dayQuery.data?.trade_date, tradeDate, searchParams, setSearchParams])

  const ensureMutation = useMutation({
    mutationFn: (date: string) => ensureReviewReport(date),
    onSuccess: (data) => {
      setReportSeed(data)
      queryClient.setQueryData(['review', 'report', data.trade_date], data)
    },
  })

  useEffect(() => {
    if (mode !== 'day') return
    if (!dayQuery.isSuccess || !dayQuery.data) return
    const ensureDate = dayQuery.data.trade_date
    if (ensuredDateRef.current === ensureDate) return
    ensuredDateRef.current = ensureDate
    ensureMutation.mutate(ensureDate)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- once per successful day fetch
  }, [mode, dayQuery.isSuccess, dayQuery.data?.trade_date])

  const setMode = (next: ReviewMode) => {
    const nextParams = new URLSearchParams(searchParams)
    if (next === 'day') {
      nextParams.delete('themeId')
      if (!nextParams.get('date')) nextParams.set('date', tradeDate)
    } else {
      if (themeId != null) {
        nextParams.set('themeId', String(themeId))
      } else if (themeIdInput.trim()) {
        nextParams.set('themeId', themeIdInput.trim())
      } else {
        nextParams.set('themeId', '1')
        setThemeIdInput('1')
      }
    }
    setSearchParams(nextParams, { replace: true })
  }

  const setDate = (value: string) => {
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('date', resolveTradeDateIso(value))
    nextParams.delete('themeId')
    setSearchParams(nextParams, { replace: true })
  }

  const applyThemeId = () => {
    const parsed = parseThemeId(themeIdInput.trim())
    if (parsed == null) return
    const nextParams = new URLSearchParams(searchParams)
    nextParams.set('themeId', String(parsed))
    setSearchParams(nextParams, { replace: true })
  }

  const selectDateFromTheme = (date: string) => {
    setSearchParams({ date: resolveTradeDateIso(date) }, { replace: true })
  }

  const subtitle = useMemo(() => {
    if (mode === 'theme') return '按题材回看阶段轨迹与关联候选'
    return '按交易日回放策略、候选与涨跌验证'
  }, [mode])

  return (
    <div className="min-h-screen">
      <AppCardNav />
      <main className="mx-auto w-full max-w-none space-y-6 px-3 py-6 sm:px-4 lg:px-5 xl:px-6">
        <GlowCard>
          <section className="space-y-4 p-6 sm:p-8">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <BookOpen className="h-5 w-5" aria-hidden="true" />
                </div>
                <div>
                  <h1 className="text-xl font-semibold tracking-tight">复盘台</h1>
                  <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
                </div>
              </div>

              <div
                className="flex flex-wrap items-center gap-1 rounded-xl bg-muted/60 p-1"
                role="group"
                aria-label="复盘模式"
              >
                <button
                  type="button"
                  aria-pressed={mode === 'day'}
                  onClick={() => setMode('day')}
                  className={cn(
                    'rounded-xl px-3 py-1.5 text-sm font-medium transition-colors',
                    mode === 'day'
                      ? 'bg-background text-foreground shadow-sm'
                      : 'text-muted-foreground hover:text-foreground'
                  )}
                >
                  交易日
                </button>
                <button
                  type="button"
                  aria-pressed={mode === 'theme'}
                  onClick={() => setMode('theme')}
                  className={cn(
                    'rounded-xl px-3 py-1.5 text-sm font-medium transition-colors',
                    mode === 'theme'
                      ? 'bg-background text-foreground shadow-sm'
                      : 'text-muted-foreground hover:text-foreground'
                  )}
                >
                  题材
                </button>
              </div>
            </div>

            {mode === 'day' ? (
              <label className="flex flex-wrap items-center gap-2 text-sm">
                <span className="text-muted-foreground">交易日</span>
                <input
                  type="date"
                  value={tradeDate}
                  onChange={(e) => setDate(e.target.value)}
                  className="rounded-lg border border-border bg-background px-3 py-1.5 tabular-nums"
                />
              </label>
            ) : (
              <div className="flex flex-wrap items-end gap-2">
                <label className="flex flex-col gap-1 text-sm">
                  <span className="text-muted-foreground">题材 ID</span>
                  <input
                    type="number"
                    min={1}
                    step={1}
                    value={themeIdInput}
                    onChange={(e) => setThemeIdInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        applyThemeId()
                      }
                    }}
                    className="w-36 rounded-lg border border-border bg-background px-3 py-1.5 tabular-nums"
                  />
                </label>
                <button
                  type="button"
                  onClick={applyThemeId}
                  className="rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground"
                >
                  加载
                </button>
              </div>
            )}
          </section>
        </GlowCard>

        <GlowCard>
          <div className="p-6 sm:p-8">
            {mode === 'day' ? (
              dayQuery.isLoading ? (
                <p className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  加载日复盘…
                </p>
              ) : dayQuery.isError ? (
                <p className="text-sm text-destructive">日复盘加载失败</p>
              ) : dayQuery.data ? (
                <ReviewDayPanel
                  day={dayQuery.data}
                  reportSeed={reportSeed}
                  ensurePending={ensureMutation.isPending}
                />
              ) : null
            ) : themeId == null ? (
              <p className="text-sm text-muted-foreground">请输入有效的题材 ID</p>
            ) : themeQuery.isLoading ? (
              <p className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                加载题材轴…
              </p>
            ) : themeQuery.isError ? (
              <p className="text-sm text-destructive">题材轴加载失败</p>
            ) : themeQuery.data ? (
              <ReviewThemePanel theme={themeQuery.data} onSelectDate={selectDateFromTheme} />
            ) : null}
          </div>
        </GlowCard>
      </main>
    </div>
  )
}
