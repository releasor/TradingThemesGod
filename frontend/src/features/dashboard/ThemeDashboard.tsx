/** 题材看板主页面
 *
 * 展示热门题材排名，支持加载、错误和空状态。
 */

import { useQuery, useQueryClient, keepPreviousData } from '@tanstack/react-query'
import dayjs from 'dayjs'
import { useCallback, useEffect, useMemo, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  fetchIndicatorSignals,
  fetchMarketSignals,
  fetchThemeRanking,
  fetchThemes,
} from '@/api/theme'
import {
  fetchFirstToSecondCandidates,
  fetchShortTermOverview,
  fetchShortTermSectors,
  refreshFirstToSecondCandidates,
  refreshShortTermData,
  refreshShortTermSignals,
} from '@/api/short-term'
import {
  fetchLatestSuccessfulRun,
  fetchDashboardScraperSources,
  refreshThemeQuotes,
  runScraperRaceAndWait,
  type ScraperRace,
} from '@/api/scraper'
import { fetchSystemStats } from '@/api/stats'
import { useAuthStore } from '@/stores/auth'
import { useDashboardStore } from '@/stores/dashboard'
import { useRefreshTimer, formatRefreshDurationMs, quoteSourceLabel } from '@/hooks/useRefreshTimer'
import { ThemeCard } from '@/components/ThemeCard'
import { ThemeCardSkeleton } from '@/components/ThemeCardSkeleton'
import { QuickStats } from '@/components/QuickStats'
import { ThemeRiseFallBar } from '@/components/charts/ThemeRiseFallBar'
import { LoadingBar } from '@/components/LoadingBar'
import { EmptyState } from '@/components/EmptyState'
import { ErrorDisplay } from '@/components/ErrorDisplay'
import { DashboardRefreshControls } from '@/components/DashboardRefreshControls'
import { DashboardRefreshStatus } from '@/components/DashboardRefreshStatus'
import { AppCardNav } from '@/components/AppCardNav'
import { DASHBOARD_REFRESH_EVENT } from '@/components/GlobalKeyboardShortcuts'
import { ToastContainer, useToast } from '@/components/Toast'
import { MarketSignalSection } from '@/components/MarketSignalSection'
import { BoardUpgradeReference } from '@/components/BoardUpgradeReference'
import { NewsTimeline } from '@/components/NewsTimeline'
import { MarketStrategyCard } from '@/components/short-term/MarketStrategyCard'
import { ShortTermRadarSection } from '@/components/short-term/ShortTermRadarSection'
import { GlowCard } from '@/components/GlowCard'
import { strategyCardQueryKey } from '@/features/dashboard/strategyCardQuery'
import {
  SECTION_IDS,
  type SectionId,
  formatSectionRefreshedAt,
  readSectionRefreshedAt,
  writeSectionRefreshedAt,
} from '@/features/dashboard/sectionRefresh'
import { isCancelledError } from '@/lib/react-query'
import type {
  ShortTermOverviewResponse,
  ShortTermPeriod,
  ShortTermPeriodStatus,
} from '@/types/short-term'

function formatServerTime(value: string): string {
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)
  return dayjs(hasTimezone ? value : `${value}Z`).format('YYYY-MM-DD HH:mm:ss')
}

type UpdateResult = {
  type: 'progress' | 'success' | 'error' | 'info'
  message: string
} | null

type RefreshSession = {
  controller: AbortController
  mode: 'light' | 'full'
}

type SectionTimesState = Record<SectionId, string | null>

const latestScraperRunQueryKey = (source: string) =>
  ['latest-successful-scraper-run', source] as const

function sourceLabelFor(
  sourceId: string | null | undefined,
  sources: { id: string; label: string }[]
): string {
  if (!sourceId) return '未知数据源'
  return sources.find((item) => item.id === sourceId)?.label ?? sourceId
}

function formatRaceProgressMessage(
  race: Pick<ScraperRace, 'phase' | 'progress_pct' | 'winner' | 'sources'>,
  elapsed: string,
  sources: { id: string; label: string }[]
): string {
  const pct = Math.round(race.progress_pct)
  const winnerLabel = race.winner ? sourceLabelFor(race.winner, sources) : null
  const leading = [...(race.sources ?? [])]
    .filter((item) => item.status === 'running' || item.status === 'completed')
    .sort((a, b) => b.progress_pct - a.progress_pct)[0]
  const leadingHint =
    leading && leading.progress_pct > 0
      ? `（${sourceLabelFor(leading.id, sources)} ${Math.round(leading.progress_pct)}%）`
      : ''

  if (race.phase === 'committing') {
    return winnerLabel
      ? `已选定 ${winnerLabel}，落库中 ${pct}%（已耗时 ${elapsed}）...`
      : `落库中 ${pct}%（已耗时 ${elapsed}）...`
  }
  if (race.phase === 'selecting' && winnerLabel) {
    return `已选定 ${winnerLabel} ${pct}%（已耗时 ${elapsed}）...`
  }
  if (winnerLabel) {
    return `多源竞速中，领先 ${winnerLabel} ${pct}%（已耗时 ${elapsed}）...`
  }
  return `多源竞速中 ${pct}%${leadingHint}（已耗时 ${elapsed}）...`
}

const SHORT_TERM_PERIOD_LABELS: Record<ShortTermPeriod, string> = {
  today: '当日',
  current_week: '本周',
  half_month: '近半月',
  current_month: '本月',
  custom: '自定义',
}

function defaultCustomStartDate(endDate: string): string {
  return dayjs(endDate).subtract(14, 'day').format('YYYY-MM-DD')
}

function shortTermErrorMessage(error: unknown): string {
  const value = error as {
    response?: { data?: { detail?: string }; status?: number }
    message?: string
  }
  return value.response?.data?.detail || value.message || '操作失败'
}

function apiErrorStatus(error: unknown): number | undefined {
  const value = error as { response?: { status?: number } }
  return value.response?.status
}

function formatRefreshProgress(done: string[], pending: string | null, elapsed: string): string {
  const donePart = done.length > 0 ? `已更新：${done.join('；')}。` : ''
  if (!pending) return donePart.replace(/。$/, '')
  return `${donePart}正在更新：${pending}（已耗时 ${elapsed}）...`
}

/** 轻量/分板块阶段 → 进度百分比（全量竞速结束后映射到 70–100） */
function sectionPhaseProgress(pending: string | null, racePhase = false): number {
  const base: Record<string, number> = {
    题材行情: 12,
    '热度榜 / 涨幅榜 / 信号': 35,
    热度榜: 28,
    涨幅榜: 32,
    策略卡: 55,
    短线信号: 75,
    一进二: 90,
  }
  if (pending === null) return 100
  const raw = base[pending] ?? 40
  if (!racePhase) return raw
  return Math.round(70 + (raw / 100) * 30)
}

function mapRaceProgressToOverall(racePct: number): number {
  return Math.round(Math.min(70, Math.max(0, racePct) * 0.7))
}

function initialSectionTimes(): SectionTimesState {
  return {
    [SECTION_IDS.heatRanking]: readSectionRefreshedAt(SECTION_IDS.heatRanking),
    [SECTION_IDS.riseRanking]: readSectionRefreshedAt(SECTION_IDS.riseRanking),
    [SECTION_IDS.strategyCard]: readSectionRefreshedAt(SECTION_IDS.strategyCard),
    [SECTION_IDS.shortTermRadar]: readSectionRefreshedAt(SECTION_IDS.shortTermRadar),
    [SECTION_IDS.firstToSecond]: readSectionRefreshedAt(SECTION_IDS.firstToSecond),
    [SECTION_IDS.marketSignals]: readSectionRefreshedAt(SECTION_IDS.marketSignals),
    [SECTION_IDS.indicatorSignals]: readSectionRefreshedAt(SECTION_IDS.indicatorSignals),
  }
}

export function ThemeDashboard() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const limit = useDashboardStore((s) => s.limit)
  const token = useAuthStore((s) => s.token)
  const toast = useToast()
  const [isUpdating, setIsUpdating] = useState(false)
  const [refreshProgressPct, setRefreshProgressPct] = useState<number | null>(null)
  const [refreshPendingLabel, setRefreshPendingLabel] = useState<string | null>(null)
  const [refreshDoneLabels, setRefreshDoneLabels] = useState<string[]>([])
  const [lastUpdate, setLastUpdate] = useState<string | null>(null)
  const [updateResult, setUpdateResult] = useState<UpdateResult>(null)
  const [shortTermPeriod, setShortTermPeriod] = useState<ShortTermPeriod>('today')
  const [periodStatus, setPeriodStatus] = useState<ShortTermPeriodStatus | null>(null)
  const [customStartDate, setCustomStartDate] = useState<string | null>(null)
  const [customEndDate, setCustomEndDate] = useState<string | null>(null)
  const [lastStrategyOverview, setLastStrategyOverview] =
    useState<ShortTermOverviewResponse | null>(null)
  const [isDashboardRefreshing, setIsDashboardRefreshing] = useState(false)
  const [isStrategyRefreshing, setIsStrategyRefreshing] = useState(false)
  const [refreshingSections, setRefreshingSections] = useState<Partial<Record<SectionId, boolean>>>(
    {}
  )
  const [sectionTimes, setSectionTimes] = useState<SectionTimesState>(initialSectionTimes)
  const lightRefreshDoneRef = useRef<string[]>([])
  const lightRefreshPendingRef = useRef<string | null>('题材行情')
  const sessionRef = useRef<RefreshSession | null>(null)

  const sectionRefreshedAtLabels = useMemo(
    () => ({
      heatRanking: formatSectionRefreshedAt(sectionTimes[SECTION_IDS.heatRanking]),
      riseRanking: formatSectionRefreshedAt(sectionTimes[SECTION_IDS.riseRanking]),
      strategyCard: formatSectionRefreshedAt(sectionTimes[SECTION_IDS.strategyCard]),
      shortTermRadar: formatSectionRefreshedAt(sectionTimes[SECTION_IDS.shortTermRadar]),
      firstToSecond: formatSectionRefreshedAt(sectionTimes[SECTION_IDS.firstToSecond]),
    }),
    [sectionTimes]
  )

  const handleThemeClick = useCallback(
    (themeId: number) => navigate(`/themes/${themeId}`, { state: { from: '/' } }),
    [navigate]
  )

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['theme-ranking', limit],
    queryFn: () => fetchThemeRanking(limit),
    staleTime: 2 * 60 * 1000, // 2 分钟
  })
  const {
    data: riseRanking,
    isLoading: isRiseRankingLoading,
    isFetching: isRiseRankingFetching,
  } = useQuery({
    queryKey: ['theme-rise-ranking', 20],
    queryFn: () =>
      fetchThemes({
        page: 1,
        page_size: 20,
        sort_by: 'rise_fall_pct',
        sort_order: 'desc',
      }),
    staleTime: 2 * 60 * 1000,
  })
  const { data: themeCount, isFetching: isThemeCountFetching } = useQuery({
    queryKey: ['theme-count'],
    queryFn: () =>
      fetchThemes({
        page: 1,
        page_size: 1,
        sort_by: 'heat_index',
        sort_order: 'desc',
      }),
    staleTime: 2 * 60 * 1000,
  })
  const { data: systemStats } = useQuery({
    queryKey: ['system-stats'],
    queryFn: fetchSystemStats,
    staleTime: 2 * 60 * 1000,
  })
  const {
    data: marketSignals,
    isLoading: isMarketSignalsLoading,
    isError: isMarketSignalsError,
    isFetching: isMarketSignalsFetching,
  } = useQuery({
    queryKey: ['market-signals'],
    queryFn: fetchMarketSignals,
    staleTime: 2 * 60 * 1000,
  })
  const {
    data: indicatorSignals,
    isLoading: isIndicatorSignalsLoading,
    isError: isIndicatorSignalsError,
    isFetching: isIndicatorSignalsFetching,
  } = useQuery({
    queryKey: ['indicator-signals'],
    queryFn: fetchIndicatorSignals,
    staleTime: 2 * 60 * 1000,
  })
  const customRangeReady = Boolean(
    customStartDate && customEndDate && customStartDate <= customEndDate
  )
  const strategyQueryParams = useMemo(
    () => ({
      period: shortTermPeriod,
      ...(shortTermPeriod === 'custom' && customRangeReady
        ? { startDate: customStartDate!, endDate: customEndDate! }
        : {}),
    }),
    [shortTermPeriod, customRangeReady, customStartDate, customEndDate]
  )
  const databaseStrategyKey = useMemo(
    () =>
      strategyCardQueryKey(
        'database',
        shortTermPeriod,
        shortTermPeriod === 'custom' ? customStartDate : null,
        shortTermPeriod === 'custom' ? customEndDate : null
      ),
    [shortTermPeriod, customStartDate, customEndDate]
  )
  const liveStrategyKey = useMemo(
    () =>
      strategyCardQueryKey(
        'live',
        shortTermPeriod,
        shortTermPeriod === 'custom' ? customStartDate : null,
        shortTermPeriod === 'custom' ? customEndDate : null
      ),
    [shortTermPeriod, customStartDate, customEndDate]
  )
  const strategyPeriodEnabled = shortTermPeriod !== 'custom' || customRangeReady
  const {
    data: databaseStrategyOverview,
    isFetching: isDatabaseStrategyFetching,
    isError: isDatabaseStrategyError,
    isPlaceholderData: isDatabaseStrategyPlaceholder,
    error: databaseStrategyError,
  } = useQuery({
    queryKey: databaseStrategyKey,
    queryFn: () => fetchShortTermOverview(strategyQueryParams),
    enabled: strategyPeriodEnabled,
    staleTime: 2 * 60 * 1000,
    placeholderData: keepPreviousData,
    retry: false,
  })
  const { data: liveStrategyOverview } = useQuery({
    queryKey: liveStrategyKey,
    queryFn: async () => {
      throw new Error('实时策略数据请通过上方「刷新」获取')
    },
    enabled: false,
    staleTime: Infinity,
  })
  const databaseOverviewMatches = useMemo(() => {
    if (!databaseStrategyOverview || isDatabaseStrategyPlaceholder) return false
    if (shortTermPeriod !== databaseStrategyOverview.period) return false
    if (shortTermPeriod !== 'custom') return true
    return (
      databaseStrategyOverview.start_date === customStartDate &&
      databaseStrategyOverview.end_date === customEndDate
    )
  }, [
    customEndDate,
    customStartDate,
    databaseStrategyOverview,
    isDatabaseStrategyPlaceholder,
    shortTermPeriod,
  ])
  const isStrategyPreview =
    !liveStrategyOverview && Boolean(databaseStrategyOverview?.strategy_card)
  const strategyOverviewForCard = useMemo(() => {
    return liveStrategyOverview ?? databaseStrategyOverview ?? lastStrategyOverview
  }, [databaseStrategyOverview, lastStrategyOverview, liveStrategyOverview])
  const isStrategyPeriodLoading =
    isStrategyRefreshing ||
    (isDatabaseStrategyFetching && !databaseOverviewMatches && !liveStrategyOverview)
  const { elapsedLabel: strategyRefreshElapsed } = useRefreshTimer(isStrategyRefreshing)

  const {
    data: firstToSecondCandidates,
    isLoading: isFirstToSecondLoading,
    isFetching: isFirstToSecondFetching,
  } = useQuery({
    queryKey: ['first-to-second-candidates'],
    queryFn: () => fetchFirstToSecondCandidates({}),
    staleTime: 60 * 1000,
    retry: 1,
  })

  const { data: dashboardScraperSources = [] } = useQuery({
    queryKey: ['dashboard-scraper-sources'],
    queryFn: fetchDashboardScraperSources,
    staleTime: 10 * 60 * 1000,
  })

  const { data: latestSuccessfulUpdate, refetch: refetchLatestSuccessfulUpdate } = useQuery({
    queryKey: latestScraperRunQueryKey('eastmoney'),
    queryFn: async () => (await fetchLatestSuccessfulRun('eastmoney'))?.finished_at ?? null,
    staleTime: 2 * 60 * 1000,
  })

  const { elapsedLabel: dashboardRefreshElapsed } = useRefreshTimer(isDashboardRefreshing)
  const { elapsedLabel: fullUpdateElapsed } = useRefreshTimer(isUpdating)

  const setSectionBusy = useCallback((sectionId: SectionId, busy: boolean) => {
    setRefreshingSections((prev) => {
      if (Boolean(prev[sectionId]) === busy) return prev
      return { ...prev, [sectionId]: busy }
    })
  }, [])

  const clearSectionBusy = useCallback(() => {
    setRefreshingSections({})
    setIsStrategyRefreshing(false)
  }, [])

  const commitSection = useCallback(
    async <T,>(
      sectionId: SectionId,
      queryKey: unknown[],
      fetcher: (signal: AbortSignal) => Promise<T>,
      signal: AbortSignal
    ): Promise<boolean> => {
      setSectionBusy(sectionId, true)
      try {
        const data = await fetcher(signal)
        if (signal.aborted) return false
        queryClient.setQueryData(queryKey, data)
        const iso = new Date().toISOString()
        writeSectionRefreshedAt(sectionId, iso)
        setSectionTimes((prev) => ({ ...prev, [sectionId]: iso }))
        return true
      } catch (e) {
        if (isCancelledError(e) || signal.aborted) return false
        throw e
      } finally {
        setSectionBusy(sectionId, false)
      }
    },
    [queryClient, setSectionBusy]
  )

  const cancelRefresh = useCallback(() => {
    sessionRef.current?.controller.abort()
    sessionRef.current = null
    setIsDashboardRefreshing(false)
    setIsUpdating(false)
    setRefreshProgressPct(null)
    setRefreshPendingLabel(null)
    setRefreshDoneLabels([])
    clearSectionBusy()
    lightRefreshPendingRef.current = null
    setUpdateResult({ type: 'info', message: '已取消，已保留成功板块' })
  }, [clearSectionBusy])

  const publishProgress = useCallback(
    (
      done: string[],
      pending: string | null,
      startedAt: number,
      mode: 'light' | 'full'
    ) => {
      lightRefreshDoneRef.current = [...done]
      lightRefreshPendingRef.current = pending
      setRefreshDoneLabels([...done])
      setRefreshPendingLabel(pending)
      setRefreshProgressPct(sectionPhaseProgress(pending, mode === 'full'))
      if (mode === 'full' && !pending) return
      setUpdateResult({
        type: 'progress',
        message: formatRefreshProgress(
          done,
          pending,
          formatRefreshDurationMs(Date.now() - startedAt)
        ),
      })
    },
    []
  )

  const runSectionPipeline = useCallback(
    async (
      signal: AbortSignal,
      done: string[],
      skipped: string[],
      startedAt: number,
      mode: 'light' | 'full'
    ) => {
      const mark = (pending: string | null) => publishProgress(done, pending, startedAt, mode)

      mark('热度榜 / 涨幅榜 / 信号')
      const rankingResults = await Promise.allSettled([
        commitSection(
          SECTION_IDS.heatRanking,
          ['theme-ranking', limit],
          (s) => fetchThemeRanking(limit, s),
          signal
        ),
        commitSection(
          SECTION_IDS.riseRanking,
          ['theme-rise-ranking', 20],
          (s) =>
            fetchThemes(
              {
                page: 1,
                page_size: 20,
                sort_by: 'rise_fall_pct',
                sort_order: 'desc',
              },
              s
            ),
          signal
        ),
        commitSection(
          SECTION_IDS.marketSignals,
          ['market-signals'],
          (s) => fetchMarketSignals(s),
          signal
        ),
        commitSection(
          SECTION_IDS.indicatorSignals,
          ['indicator-signals'],
          (s) => fetchIndicatorSignals(s),
          signal
        ),
        (async () => {
          try {
            const data = await fetchThemes(
              {
                page: 1,
                page_size: 1,
                sort_by: 'heat_index',
                sort_order: 'desc',
              },
              signal
            )
            if (signal.aborted) return false
            queryClient.setQueryData(['theme-count'], data)
            return true
          } catch (e) {
            if (isCancelledError(e) || signal.aborted) return false
            throw e
          }
        })(),
        (async () => {
          try {
            const data = await fetchSystemStats(signal)
            if (signal.aborted) return false
            queryClient.setQueryData(['system-stats'], data)
            return true
          } catch (e) {
            if (isCancelledError(e) || signal.aborted) return false
            throw e
          }
        })(),
      ])
      if (signal.aborted) return
      const rankingLabels = ['热度榜', '涨幅榜', '市场表现', '行情指标'] as const
      rankingResults.slice(0, 4).forEach((result, index) => {
        if (result.status === 'fulfilled' && result.value) {
          done.push(rankingLabels[index])
        } else if (result.status === 'rejected') {
          skipped.push(`${rankingLabels[index]}失败：${shortTermErrorMessage(result.reason)}`)
        }
      })

      if (strategyPeriodEnabled) {
        if (shortTermPeriod === 'custom' && (!customStartDate || !customEndDate)) {
          skipped.push('策略卡（未选自定义日期）')
          setPeriodStatus({
            type: 'error',
            message: '请先选择自定义日期范围后再刷新策略卡',
          })
        } else {
          mark('策略卡')
          setIsStrategyRefreshing(true)
          setPeriodStatus({ type: 'progress', message: '正在拉取实时行情并更新策略卡...' })
          try {
            const data = await refreshShortTermData(strategyQueryParams, signal)
            if (signal.aborted) return
            const liveKey = strategyCardQueryKey(
              'live',
              strategyQueryParams.period,
              strategyQueryParams.period === 'custom'
                ? (strategyQueryParams.startDate ?? null)
                : null,
              strategyQueryParams.period === 'custom' ? (strategyQueryParams.endDate ?? null) : null
            )
            queryClient.setQueryData(liveKey, data)
            setLastStrategyOverview(data)
            const iso = new Date().toISOString()
            writeSectionRefreshedAt(SECTION_IDS.strategyCard, iso)
            setSectionTimes((prev) => ({ ...prev, [SECTION_IDS.strategyCard]: iso }))
            done.push('策略卡')
            const meta = data.refresh_meta
            const degraded = Boolean(meta?.quote_message) || meta?.quote_source === 'database'
            const timing = meta?.elapsed_ms
              ? `，耗时 ${formatRefreshDurationMs(meta.elapsed_ms)}`
              : ''
            const source =
              meta && !degraded ? `，数据源 ${quoteSourceLabel(meta.quote_source)}` : ''
            const attempts =
              meta && meta.quote_attempts.length > 1
                ? `（${meta.quote_attempts.map(quoteSourceLabel).join(' → ')}）`
                : ''
            setPeriodStatus({
              type: degraded ? 'error' : 'success',
              message: degraded
                ? meta?.quote_message || `实时行情不可用，已回退数据库数据${attempts}`
                : `${SHORT_TERM_PERIOD_LABELS[strategyQueryParams.period]}策略卡实时数据已更新${timing}${source}${attempts}`,
            })
          } catch (strategyError) {
            if (isCancelledError(strategyError) || signal.aborted) return
            skipped.push(`策略卡失败：${shortTermErrorMessage(strategyError)}`)
            setPeriodStatus({
              type: 'error',
              message: `实时行情刷新失败：${shortTermErrorMessage(strategyError)}`,
            })
            toast.error(`策略卡刷新失败：${shortTermErrorMessage(strategyError)}`)
          } finally {
            setIsStrategyRefreshing(false)
          }
        }
      }

      if (signal.aborted) return

      if (token) {
        mark('短线信号')
        setSectionBusy(SECTION_IDS.shortTermRadar, true)
        try {
          const signals = await refreshShortTermSignals(undefined, signal)
          if (signal.aborted) return
          const sectorsOk = await commitSection(
            SECTION_IDS.shortTermRadar,
            ['short-term-sectors'],
            (s) => fetchShortTermSectors(undefined, s),
            signal
          )
          if (signal.aborted) return
          if (signals.status === 'failed') {
            skipped.push(signals.error_message || '短线信号失败')
          } else if (sectorsOk) {
            done.push(
              `短线信号（涨停${signals.signal_count}/龙虎${signals.dragon_tiger_count}/轮动${signals.sector_count}）`
            )
            if (signals.degraded && signals.missing_sources.length > 0) {
              skipped.push(`短线源缺失：${signals.missing_sources.join('、')}`)
            }
          } else {
            skipped.push('短线信号（板块数据未更新）')
          }
        } catch (signalError) {
          if (isCancelledError(signalError) || signal.aborted) return
          skipped.push(`短线信号失败：${shortTermErrorMessage(signalError)}`)
        } finally {
          setSectionBusy(SECTION_IDS.shortTermRadar, false)
        }
      } else {
        skipped.push('短线信号（未登录）')
      }

      if (signal.aborted) return

      mark('一进二')
      setSectionBusy(SECTION_IDS.firstToSecond, true)
      try {
        await refreshFirstToSecondCandidates({}, signal)
        if (signal.aborted) return
        const ok = await commitSection(
          SECTION_IDS.firstToSecond,
          ['first-to-second-candidates'],
          (s) => fetchFirstToSecondCandidates({}, s),
          signal
        )
        if (ok) done.push('一进二')
        else if (!signal.aborted) skipped.push('一进二（未更新）')
      } catch (firstError) {
        if (isCancelledError(firstError) || signal.aborted) return
        skipped.push(`一进二失败：${shortTermErrorMessage(firstError)}`)
      } finally {
        setSectionBusy(SECTION_IDS.firstToSecond, false)
      }

      mark(null)
    },
    [
      commitSection,
      customEndDate,
      customStartDate,
      limit,
      publishProgress,
      queryClient,
      setSectionBusy,
      shortTermPeriod,
      strategyPeriodEnabled,
      strategyQueryParams,
      toast,
      token,
    ]
  )

  const handleLightRefresh = useCallback(async () => {
    if (sessionRef.current) return

    const controller = new AbortController()
    const session: RefreshSession = { controller, mode: 'light' }
    sessionRef.current = session
    const { signal } = controller
    const startedAt = Date.now()
    const done: string[] = []
    const skipped: string[] = []
    lightRefreshDoneRef.current = []
    lightRefreshPendingRef.current = '题材行情'
    setIsDashboardRefreshing(true)
    setRefreshProgressPct(sectionPhaseProgress('题材行情'))
    setRefreshPendingLabel('题材行情')
    setRefreshDoneLabels([])
    setUpdateResult({
      type: 'progress',
      message: formatRefreshProgress(done, '题材行情', '0 秒'),
    })

    try {
      let quotes
      try {
        quotes = await refreshThemeQuotes(signal)
      } catch (quotesError) {
        if (isCancelledError(quotesError) || signal.aborted) return
        if (apiErrorStatus(quotesError) === 409) {
          throw new Error(
            shortTermErrorMessage(quotesError) || '行情刷新进行中，请稍后再试'
          )
        }
        throw quotesError
      }
      if (signal.aborted) return
      const refreshedAt = quotes.refreshed_at || new Date().toISOString()
      setLastUpdate(refreshedAt)
      done.push(`题材行情 ${quotes.themes_updated} 个`)
      publishProgress(done, strategyPeriodEnabled ? '策略卡' : token ? '短线信号' : '热度榜', startedAt, 'light')

      await runSectionPipeline(signal, done, skipped, startedAt, 'light')
      if (signal.aborted) return

      const elapsedSeconds = Math.max(1, Math.round((Date.now() - startedAt) / 1000))
      const refreshedLabel = formatServerTime(refreshedAt)
      const summary = [
        done.length > 0 ? `已更新：${done.join('；')}` : null,
        skipped.length > 0 ? `未完成：${skipped.join('；')}` : null,
        `更新于 ${refreshedLabel}，耗时 ${elapsedSeconds} 秒`,
      ]
        .filter(Boolean)
        .join('。')
      lightRefreshPendingRef.current = null
      lightRefreshDoneRef.current = [...done]
      setRefreshProgressPct(100)
      setRefreshPendingLabel(null)
      setRefreshDoneLabels([...done])
      setUpdateResult({
        type: skipped.length > 0 && done.length === 0 ? 'error' : 'success',
        message: summary,
      })
      if (skipped.length > 0 && done.length > 0) {
        toast.success(`部分刷新完成：${done.join('；')}`)
      } else if (done.length > 0) {
        toast.success(`已刷新：${done.join('；')}`)
      }
    } catch (error) {
      if (isCancelledError(error) || signal.aborted) return
      const message = error instanceof Error ? error.message : '未知错误'
      const partial = done.length > 0 ? `已更新：${done.join('；')}。` : ''
      setUpdateResult({
        type: 'error',
        message: `${partial}看板刷新失败：${message}`,
      })
      toast.error(`看板刷新失败：${message}`)
    } finally {
      if (sessionRef.current === session) {
        sessionRef.current = null
        setIsDashboardRefreshing(false)
        clearSectionBusy()
        lightRefreshPendingRef.current = null
        window.setTimeout(() => {
          setRefreshProgressPct(null)
          setRefreshPendingLabel(null)
        }, 800)
      }
    }
  }, [
    clearSectionBusy,
    publishProgress,
    runSectionPipeline,
    strategyPeriodEnabled,
    toast,
    token,
  ])

  useEffect(() => {
    if (!isDashboardRefreshing) return
    setUpdateResult((current) => {
      if (current?.type === 'success' || current?.type === 'error' || current?.type === 'info') {
        return current
      }
      return {
        type: 'progress',
        message: formatRefreshProgress(
          lightRefreshDoneRef.current,
          lightRefreshPendingRef.current,
          dashboardRefreshElapsed
        ),
      }
    })
  }, [dashboardRefreshElapsed, isDashboardRefreshing])

  const updateDashboard = useCallback(async () => {
    if (sessionRef.current) return

    const controller = new AbortController()
    const session: RefreshSession = { controller, mode: 'full' }
    sessionRef.current = session
    const { signal } = controller
    const startedAt = Date.now()
    const done: string[] = []
    const skipped: string[] = []

    setIsUpdating(true)
    setRefreshProgressPct(0)
    setRefreshPendingLabel('多源竞速')
    setRefreshDoneLabels([])
    setUpdateResult({
      type: 'progress',
      message: '多源竞速中 0%（已耗时 0 秒）...',
    })
    try {
      const race = await runScraperRaceAndWait({
        signal,
        onProgress: (nextRace) => {
          if (signal.aborted) return
          const pct = mapRaceProgressToOverall(nextRace.progress_pct)
          setRefreshProgressPct(pct)
          const leading = [...(nextRace.sources ?? [])]
            .filter((item) => item.status === 'running' || item.status === 'completed')
            .sort((a, b) => b.progress_pct - a.progress_pct)[0]
          const pending =
            nextRace.phase === 'committing'
              ? '落库'
              : leading && leading.progress_pct > 0
                ? `竞速 · ${sourceLabelFor(leading.id, dashboardScraperSources)} ${Math.round(leading.progress_pct)}%`
                : nextRace.winner
                  ? `竞速（领先 ${sourceLabelFor(nextRace.winner, dashboardScraperSources)}）`
                  : '多源竞速'
          setRefreshPendingLabel(pending)
          setUpdateResult({
            type: 'progress',
            message: formatRaceProgressMessage(
              nextRace,
              formatRefreshDurationMs(Date.now() - startedAt),
              dashboardScraperSources
            ),
          })
        },
      })
      if (signal.aborted) return
      if (race.status === 'failed') {
        const message = `全量更新失败：${race.error || '未知错误'}`
        setUpdateResult({ type: 'error', message })
        toast.error(message)
        return
      }
      if (race.status === 'cancelled') {
        return
      }
      if (race.status !== 'completed') {
        const message = `全量更新失败：${race.error || `竞速状态 ${race.status}`}`
        setUpdateResult({ type: 'error', message })
        toast.error(message)
        return
      }

      const finishedAt = new Date().toISOString()
      const winnerSource = race.winner ?? 'eastmoney'
      setLastUpdate(finishedAt)
      queryClient.setQueryData(latestScraperRunQueryKey(winnerSource), finishedAt)
      await refetchLatestSuccessfulUpdate()

      // 竞速落库完成 → 继续分板块刷新，进度条保持确定进度（70%→100%）
      setRefreshProgressPct(70)
      setRefreshDoneLabels([
        `全量落库（${sourceLabelFor(winnerSource, dashboardScraperSources)}）`,
      ])
      publishProgress(done, '题材行情', startedAt, 'full')

      try {
        const quotes = await refreshThemeQuotes(signal)
        if (signal.aborted) return
        done.push(`题材行情 ${quotes.themes_updated} 个`)
        setLastUpdate(quotes.refreshed_at || finishedAt)
      } catch (quotesError) {
        if (isCancelledError(quotesError) || signal.aborted) return
        skipped.push(`题材行情失败：${shortTermErrorMessage(quotesError)}`)
      }

      await runSectionPipeline(signal, done, skipped, startedAt, 'full')
      if (signal.aborted) return

      const usedSourceLabel = sourceLabelFor(winnerSource, dashboardScraperSources)
      const elapsedSeconds = Math.max(1, Math.round((Date.now() - startedAt) / 1000))
      const itemsScraped = race.items_scraped ?? 0
      const sectionSummary =
        done.length > 0 || skipped.length > 0
          ? `。${[
              done.length > 0 ? `已更新：${done.join('；')}` : null,
              skipped.length > 0 ? `未完成：${skipped.join('；')}` : null,
            ]
              .filter(Boolean)
              .join('。')}`
          : ''
      setRefreshProgressPct(100)
      setRefreshPendingLabel(null)
      setRefreshDoneLabels([...done])
      setUpdateResult({
        type: 'success',
        message: `${usedSourceLabel}全量更新成功，共更新 ${itemsScraped} 条数据，耗时 ${elapsedSeconds} 秒${sectionSummary}`,
      })
      toast.success(`${usedSourceLabel}全量更新成功，共更新 ${itemsScraped} 条数据`)
    } catch (error) {
      if (isCancelledError(error) || signal.aborted) return
      const message = error instanceof Error ? error.message : '未知错误'
      setUpdateResult({ type: 'error', message: `全量更新失败：${message}` })
      toast.error(`全量更新失败：${message}`)
    } finally {
      if (sessionRef.current === session) {
        sessionRef.current = null
        setIsUpdating(false)
        setIsDashboardRefreshing(false)
        clearSectionBusy()
        lightRefreshPendingRef.current = null
        window.setTimeout(() => {
          setRefreshProgressPct(null)
          setRefreshPendingLabel(null)
        }, 800)
      }
    }
  }, [
    clearSectionBusy,
    dashboardScraperSources,
    publishProgress,
    queryClient,
    refetchLatestSuccessfulUpdate,
    runSectionPipeline,
    toast,
  ])

  // 全站快捷键 R：在看板页触发轻量刷新
  useEffect(() => {
    const onRefresh = () => {
      void handleLightRefresh()
    }
    window.addEventListener(DASHBOARD_REFRESH_EVENT, onRefresh)
    return () => window.removeEventListener(DASHBOARD_REFRESH_EVENT, onRefresh)
  }, [handleLightRefresh])

  const themes = useMemo(() => data?.items ?? [], [data?.items])
  const totalStocks = systemStats?.stocks.total ?? 0
  const formattedLastUpdate = useMemo(() => {
    const value = lastUpdate ?? latestSuccessfulUpdate
    return value ? formatServerTime(value) : null
  }, [lastUpdate, latestSuccessfulUpdate])
  const shortTermDateRange = useMemo(() => {
    if (shortTermPeriod === 'custom' && customStartDate && customEndDate) {
      if (customStartDate > customEndDate) {
        return '开始日期不能晚于结束日期'
      }
      if (customStartDate === customEndDate) {
        return customStartDate
      }
      return `${customStartDate} ~ ${customEndDate}`
    }
    if (!strategyOverviewForCard) return undefined
    if (strategyOverviewForCard.start_date === strategyOverviewForCard.end_date) {
      return strategyOverviewForCard.end_date
    }
    return `${strategyOverviewForCard.start_date} ~ ${strategyOverviewForCard.end_date}`
  }, [customEndDate, customStartDate, shortTermPeriod, strategyOverviewForCard])

  const handleNewsFeedback = useCallback(
    (type: 'success' | 'error' | 'warning', message: string) => toast[type](message),
    [toast]
  )

  const handleShortTermPeriodChange = useCallback(
    (period: ShortTermPeriod) => {
      if (period === shortTermPeriod) return
      if (period === 'custom') {
        const endDate = databaseStrategyOverview?.end_date ?? dayjs().format('YYYY-MM-DD')
        setCustomEndDate((current) => current ?? endDate)
        setCustomStartDate((current) => current ?? defaultCustomStartDate(endDate))
      }
      setPeriodStatus(null)
      setShortTermPeriod(period)
    },
    [databaseStrategyOverview?.end_date, shortTermPeriod]
  )

  const handleCustomDateRangeChange = useCallback(
    (startDate: string, endDate: string) => {
      setCustomStartDate(startDate)
      setCustomEndDate(endDate)
      if (startDate && endDate) {
        if (startDate > endDate) {
          setPeriodStatus({
            type: 'error',
            message: '开始日期不能晚于结束日期',
          })
          return
        }
        setPeriodStatus(null)
      }
      if (shortTermPeriod !== 'custom') {
        setShortTermPeriod('custom')
      }
    },
    [shortTermPeriod]
  )

  useEffect(() => {
    if (isDatabaseStrategyFetching) return
    if (liveStrategyOverview) return

    if (isDatabaseStrategyError) {
      const message =
        databaseStrategyError instanceof Error ? databaseStrategyError.message : '未知错误'
      setPeriodStatus({
        type: 'error',
        message: `策略加载失败：${message}`,
      })
      return
    }

    if (databaseOverviewMatches && databaseStrategyOverview) {
      setLastStrategyOverview(databaseStrategyOverview)
    }
  }, [
    databaseOverviewMatches,
    databaseStrategyError,
    databaseStrategyOverview,
    isDatabaseStrategyError,
    isDatabaseStrategyFetching,
    liveStrategyOverview,
  ])
  const visiblePeriodStatus = useMemo<ShortTermPeriodStatus | null>(() => {
    if (isStrategyRefreshing) {
      return {
        type: 'progress',
        message: `正在拉取实时行情并更新策略卡（已耗时 ${strategyRefreshElapsed}，东方财富慢时将自动切换 AKShare）...`,
      }
    }
    if (isStrategyPeriodLoading) {
      return {
        type: 'progress',
        message: `正在加载${shortTermDateRange ?? SHORT_TERM_PERIOD_LABELS[shortTermPeriod]}策略...`,
      }
    }
    if (periodStatus?.type === 'error') {
      return periodStatus
    }
    return periodStatus
  }, [
    isStrategyPeriodLoading,
    isStrategyRefreshing,
    periodStatus,
    shortTermDateRange,
    shortTermPeriod,
    strategyRefreshElapsed,
  ])

  const isBusy = isDashboardRefreshing || isUpdating

  return (
    <div className="min-h-screen">
      {/* 加载进度条 */}
      <LoadingBar
        isLoading={
          isLoading ||
          isFetching ||
          isRiseRankingFetching ||
          isThemeCountFetching ||
          isMarketSignalsFetching ||
          isIndicatorSignalsFetching ||
          isDashboardRefreshing ||
          Boolean(refreshingSections[SECTION_IDS.firstToSecond]) ||
          isFirstToSecondFetching ||
          isUpdating
        }
        progress={
          isDashboardRefreshing || isUpdating ? refreshProgressPct : null
        }
      />

      <AppCardNav />

      <main
        className="mx-auto w-full max-w-none px-3 py-6 sm:px-4 lg:px-5 xl:px-6"
        data-testid="dashboard-main-shell"
      >
        {/* 快速统计栏 */}
        <QuickStats
          totalThemes={themeCount?.total ?? 0}
          totalStocks={totalStocks}
          lastUpdate={formattedLastUpdate}
          actions={
            <div
              data-testid="dashboard-data-controls"
              className="flex flex-wrap items-center gap-6"
            >
              <DashboardRefreshControls
                isRefreshing={isDashboardRefreshing || isStrategyRefreshing}
                isUpdating={isUpdating}
                onRefresh={() => void handleLightRefresh()}
                onFullUpdate={() => void updateDashboard()}
                onCancel={cancelRefresh}
                refreshElapsedLabel={
                  isDashboardRefreshing || isStrategyRefreshing
                    ? dashboardRefreshElapsed || strategyRefreshElapsed
                    : undefined
                }
                updateElapsedLabel={isUpdating ? fullUpdateElapsed : undefined}
              />
            </div>
          }
        />

        <DashboardRefreshStatus
          active={isBusy}
          progressPct={refreshProgressPct}
          pendingLabel={refreshPendingLabel}
          doneLabels={refreshDoneLabels}
          message={updateResult?.message ?? null}
          messageType={updateResult?.type ?? null}
        />

        <div
          className="mt-6 grid grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(340px,1fr)]"
          data-testid="dashboard-content-grid"
        >
          <div className="min-w-0" data-testid="dashboard-main-column">
            <ShortTermRadarSection
              refreshedAtLabel={sectionRefreshedAtLabels.shortTermRadar}
              isSectionRefreshing={Boolean(refreshingSections[SECTION_IDS.shortTermRadar])}
              onSelectTheme={handleThemeClick}
            />

            {strategyOverviewForCard?.strategy_card && (
              <div className="mb-6" id="strategy">
                <MarketStrategyCard
                  card={strategyOverviewForCard.strategy_card}
                  period={shortTermPeriod}
                  periodLabel={strategyOverviewForCard.period_label}
                  dateRange={shortTermDateRange}
                  onPeriodChange={handleShortTermPeriodChange}
                  customStartDate={customStartDate ?? undefined}
                  customEndDate={customEndDate ?? undefined}
                  onCustomDateRangeChange={handleCustomDateRangeChange}
                  periodStatus={visiblePeriodStatus}
                  isPeriodLoading={isStrategyPeriodLoading || isBusy}
                  isPreview={isStrategyPreview}
                  degraded={strategyOverviewForCard.degraded}
                  missingSources={strategyOverviewForCard.missing_sources}
                  refreshedAtLabel={sectionRefreshedAtLabels.strategyCard}
                />
              </div>
            )}

            {/* 涨跌幅、行情指标与市场表现排行 */}
            <div
              className="grid grid-cols-1 gap-6 lg:grid-cols-2 xl:grid-cols-3"
              data-testid="dashboard-ranking-grid"
            >
              <section className="min-w-0">
                <div className="mb-4 flex flex-wrap items-baseline gap-2">
                  <h2 className="text-lg font-semibold text-foreground">涨跌幅 Top 20</h2>
                  <span className="text-xs text-muted-foreground">
                    刷新于 {sectionRefreshedAtLabels.riseRanking}
                  </span>
                </div>
                <GlowCard>
                  <div className="p-3">
                    {isLoading || isRiseRankingLoading ? (
                      <div className="h-[380px] animate-pulse rounded-xl bg-muted" />
                    ) : (
                      <ThemeRiseFallBar
                        themes={riseRanking?.items ?? []}
                        onThemeClick={handleThemeClick}
                      />
                    )}
                  </div>
                </GlowCard>
              </section>

              <MarketSignalSection
                title="行情指标"
                headingId="indicator-signal-heading"
                emptyText="暂无行情指标数据"
                errorText="行情指标加载失败"
                testIdPrefix="indicator-signal"
                signals={indicatorSignals?.items ?? []}
                isLoading={isIndicatorSignalsLoading}
                isError={isIndicatorSignalsError}
                onSelect={handleThemeClick}
              />

              <MarketSignalSection
                signals={marketSignals?.items ?? []}
                isLoading={isMarketSignalsLoading}
                isError={isMarketSignalsError}
                onSelect={handleThemeClick}
              />
            </div>

            {/* 热门题材 + 一进二打板参考 */}
            <div
              className="mt-6 grid grid-cols-1 items-start gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(260px,1fr)] lg:gap-5"
              data-testid="dashboard-hot-themes-grid"
            >
              <section className="min-w-0">
                <div className="mb-3 flex flex-wrap items-baseline gap-2">
                  <h2 className="text-lg font-semibold text-foreground">
                    热门题材 Top {limit}
                  </h2>
                  <span className="text-xs text-muted-foreground">
                    刷新于 {sectionRefreshedAtLabels.heatRanking}
                  </span>
                </div>
                {isLoading && (
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
                    {Array.from({ length: limit }).map((_, i) => (
                      <ThemeCardSkeleton key={i} />
                    ))}
                  </div>
                )}

                {isError && (
                  <ErrorDisplay
                    errorType={error?.message?.includes('Network') ? 'network' : 'server'}
                    onRetry={() => refetch()}
                  />
                )}

                {!isLoading && !isError && themes.length === 0 && <EmptyState type="no-data" />}

                {!isLoading && !isError && themes.length > 0 && (
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
                    {themes.map((theme) => (
                      <ThemeCard
                        key={theme.id}
                        theme={theme}
                        onClick={() => handleThemeClick(theme.id)}
                      />
                    ))}
                  </div>
                )}
              </section>

              <aside className="min-w-0 lg:sticky lg:top-24 lg:self-start">
                <BoardUpgradeReference
                  data={firstToSecondCandidates}
                  isLoading={isFirstToSecondLoading}
                  refreshedAtLabel={sectionRefreshedAtLabels.firstToSecond}
                  isSectionRefreshing={
                    Boolean(refreshingSections[SECTION_IDS.firstToSecond]) ||
                    isFirstToSecondFetching
                  }
                />
              </aside>
            </div>
          </div>

          <aside
            className="min-w-0 xl:sticky xl:top-24 xl:self-start"
            data-testid="dashboard-news-sidebar"
          >
            <NewsTimeline onFeedback={handleNewsFeedback} />
          </aside>
        </div>
      </main>
      <ToastContainer toasts={toast.toasts} onClose={toast.removeToast} />
    </div>
  )
}
