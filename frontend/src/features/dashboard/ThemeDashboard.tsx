/** 题材看板主页面
 *
 * 展示热门题材排名，支持加载、错误和空状态。
 */

import { useMutation, useQuery, useQueryClient, keepPreviousData } from '@tanstack/react-query'
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
  refreshFirstToSecondCandidates,
  refreshShortTermData,
  refreshShortTermSignals,
} from '@/api/short-term'
import { fetchLatestSuccessfulRun, fetchDashboardScraperSources, refreshThemeQuotes, runScraperWithFallback } from '@/api/scraper'
import { useAuthStore } from '@/stores/auth'
import { useDashboardStore } from '@/stores/dashboard'
import { useRefreshTimer, formatRefreshDurationMs, quoteSourceLabel } from '@/hooks/useRefreshTimer'
import { ThemeCard } from '@/components/ThemeCard'
import { ThemeCardSkeleton } from '@/components/ThemeCardSkeleton'
import { QuickStats } from '@/components/QuickStats'
import { fetchSystemStats } from '@/api/stats'
import { ThemeRiseFallBar } from '@/components/charts/ThemeRiseFallBar'
import { LoadingBar } from '@/components/LoadingBar'
import { EmptyState } from '@/components/EmptyState'
import { ErrorDisplay } from '@/components/ErrorDisplay'
import { AutoRefreshButton } from '@/components/AutoRefreshButton'
import { AppCardNav } from '@/components/AppCardNav'
import { DASHBOARD_REFRESH_EVENT } from '@/components/GlobalKeyboardShortcuts'
import { useAutoRefresh } from '@/hooks/useAutoRefresh'
import { ToastContainer, useToast } from '@/components/Toast'
import { MarketSignalSection } from '@/components/MarketSignalSection'
import { BoardUpgradeReference } from '@/components/BoardUpgradeReference'
import { NewsTimeline } from '@/components/NewsTimeline'
import { MarketStrategyCard } from '@/components/short-term/MarketStrategyCard'
import { ShortTermRadarSection } from '@/components/short-term/ShortTermRadarSection'
import { GlowCard } from '@/components/GlowCard'
import { strategyCardQueryKey } from '@/features/dashboard/strategyCardQuery'
import { isCancelledError, refetchIgnoringCancel } from '@/lib/react-query'
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
  type: 'progress' | 'success' | 'error'
  message: string
} | null

const latestScraperRunQueryKey = (source: string) =>
  ['latest-successful-scraper-run', source] as const
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
    response?: { data?: { detail?: string } }
    message?: string
  }
  return value.response?.data?.detail || value.message || '操作失败'
}

function formatRefreshProgress(done: string[], pending: string | null, elapsed: string): string {
  const donePart = done.length > 0 ? `已更新：${done.join('；')}。` : ''
  if (!pending) return donePart.replace(/。$/, '')
  return `${donePart}正在更新：${pending}（已耗时 ${elapsed}）...`
}

export function ThemeDashboard() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const limit = useDashboardStore((s) => s.limit)
  const token = useAuthStore((s) => s.token)
  const toast = useToast()
  const [isUpdating, setIsUpdating] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<string | null>(null)
  const [updateResult, setUpdateResult] = useState<UpdateResult>(null)
  const [shortTermPeriod, setShortTermPeriod] = useState<ShortTermPeriod>('today')
  const [periodStatus, setPeriodStatus] = useState<ShortTermPeriodStatus | null>(null)
  const [customStartDate, setCustomStartDate] = useState<string | null>(null)
  const [customEndDate, setCustomEndDate] = useState<string | null>(null)
  const [lastStrategyOverview, setLastStrategyOverview] =
    useState<ShortTermOverviewResponse | null>(null)
  const [isDashboardRefreshing, setIsDashboardRefreshing] = useState(false)
  const [isFirstToSecondRefreshing, setIsFirstToSecondRefreshing] = useState(false)
  const [selectedScraperSource, setSelectedScraperSource] = useState('eastmoney')
  const lightRefreshDoneRef = useRef<string[]>([])
  const lightRefreshPendingRef = useRef<string | null>('题材行情')

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
    refetch: refetchRiseRanking,
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
  const {
    data: themeCount,
    isFetching: isThemeCountFetching,
    refetch: refetchThemeCount,
  } = useQuery({
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
  const {
    data: systemStats,
    refetch: refetchSystemStats,
  } = useQuery({
    queryKey: ['system-stats'],
    queryFn: fetchSystemStats,
    staleTime: 2 * 60 * 1000,
  })
  const {
    data: marketSignals,
    isLoading: isMarketSignalsLoading,
    isError: isMarketSignalsError,
    isFetching: isMarketSignalsFetching,
    refetch: refetchMarketSignals,
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
    refetch: refetchIndicatorSignals,
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
    refetch: refetchDatabaseStrategyOverview,
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
    return (
      liveStrategyOverview ??
      databaseStrategyOverview ??
      lastStrategyOverview
    )
  }, [databaseStrategyOverview, lastStrategyOverview, liveStrategyOverview])
  const refreshStrategyDataMutation = useMutation({
    mutationFn: (params: typeof strategyQueryParams) => refreshShortTermData(params),
    onMutate: () => {
      setPeriodStatus({ type: 'progress', message: '正在拉取实时行情并更新策略卡...' })
    },
    onSuccess: (data, params) => {
      const liveKey = strategyCardQueryKey(
        'live',
        params.period,
        params.period === 'custom' ? (params.startDate ?? null) : null,
        params.period === 'custom' ? (params.endDate ?? null) : null
      )
      queryClient.setQueryData(liveKey, data)
      setLastStrategyOverview(data)
      const meta = data.refresh_meta
      const degraded = Boolean(meta?.quote_message) || meta?.quote_source === 'database'
      const timing = meta?.elapsed_ms ? `，耗时 ${formatRefreshDurationMs(meta.elapsed_ms)}` : ''
      const source = meta && !degraded ? `，数据源 ${quoteSourceLabel(meta.quote_source)}` : ''
      const attempts =
        meta && meta.quote_attempts.length > 1
          ? `（${meta.quote_attempts.map(quoteSourceLabel).join(' → ')}）`
          : ''
      setPeriodStatus({
        type: degraded ? 'error' : 'success',
        message: degraded
          ? meta?.quote_message ||
            `实时行情不可用，已回退数据库数据${attempts}`
          : `${SHORT_TERM_PERIOD_LABELS[params.period]}策略卡实时数据已更新${timing}${source}${attempts}`,
      })
    },
    onError: (error) => {
      setPeriodStatus({
        type: 'error',
        message: `实时行情刷新失败：${shortTermErrorMessage(error)}`,
      })
    },
  })
  const isStrategyPeriodLoading =
    refreshStrategyDataMutation.isPending ||
    (isDatabaseStrategyFetching && !databaseOverviewMatches && !liveStrategyOverview)
  const { elapsedLabel: strategyRefreshElapsed } = useRefreshTimer(
    refreshStrategyDataMutation.isPending
  )

  const {
    data: firstToSecondCandidates,
    isLoading: isFirstToSecondLoading,
    isFetching: isFirstToSecondFetching,
    refetch: refetchFirstToSecondCandidates,
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

  useEffect(() => {
    if (dashboardScraperSources.length === 0) return
    const defaultSource =
      dashboardScraperSources.find((item) => item.is_default)?.id ?? dashboardScraperSources[0].id
    setSelectedScraperSource((current) =>
      dashboardScraperSources.some((item) => item.id === current) ? current : defaultSource
    )
  }, [dashboardScraperSources])

  const selectedScraperSourceLabel = useMemo(
    () =>
      dashboardScraperSources.find((item) => item.id === selectedScraperSource)?.label ??
      selectedScraperSource,
    [dashboardScraperSources, selectedScraperSource]
  )

  const { data: latestSuccessfulUpdate, refetch: refetchLatestSuccessfulUpdate } = useQuery({
    queryKey: latestScraperRunQueryKey(selectedScraperSource),
    queryFn: async () =>
      (await fetchLatestSuccessfulRun(selectedScraperSource))?.finished_at ?? null,
    staleTime: 2 * 60 * 1000,
  })

  const { elapsedLabel: dashboardRefreshElapsed } = useRefreshTimer(isDashboardRefreshing)
  const { elapsedLabel: fullUpdateElapsed } = useRefreshTimer(isUpdating)

  const refreshInFlightRef = useRef<Promise<void> | null>(null)

  const refreshMainDashboard = useCallback(async () => {
    if (refreshInFlightRef.current) {
      return refreshInFlightRef.current
    }

    const run = (async () => {
      const tasks = [
        refetchIgnoringCancel(refetch),
        refetchIgnoringCancel(refetchRiseRanking),
        refetchIgnoringCancel(refetchThemeCount),
        refetchIgnoringCancel(refetchSystemStats),
        refetchIgnoringCancel(refetchMarketSignals),
        refetchIgnoringCancel(refetchIndicatorSignals),
        ...(strategyPeriodEnabled
          ? [refetchIgnoringCancel(refetchDatabaseStrategyOverview)]
          : []),
      ]
      await Promise.all(tasks)
      // 一进二需登录，失败不应卡住整页刷新
      await refetchIgnoringCancel(refetchFirstToSecondCandidates).catch(() => undefined)
    })()

    refreshInFlightRef.current = run
    try {
      await run
    } finally {
      if (refreshInFlightRef.current === run) {
        refreshInFlightRef.current = null
      }
    }
  }, [
    refetch,
    refetchDatabaseStrategyOverview,
    refetchFirstToSecondCandidates,
    refetchIndicatorSignals,
    refetchMarketSignals,
    refetchRiseRanking,
    refetchSystemStats,
    refetchThemeCount,
    strategyPeriodEnabled,
  ])

  const handleLightRefresh = useCallback(async (options?: { silent?: boolean }) => {
    const startedAt = Date.now()
    const done: string[] = []
    const skipped: string[] = []
    lightRefreshDoneRef.current = []
    lightRefreshPendingRef.current = '题材行情'
    setIsDashboardRefreshing(true)
    setUpdateResult({
      type: 'progress',
      message: formatRefreshProgress(done, '题材行情', '0 秒'),
    })

    const publishProgress = (pending: string | null) => {
      lightRefreshDoneRef.current = [...done]
      lightRefreshPendingRef.current = pending
      setUpdateResult({
        type: 'progress',
        message: formatRefreshProgress(
          done,
          pending,
          formatRefreshDurationMs(Date.now() - startedAt)
        ),
      })
    }

    try {
      const quotes = await refreshThemeQuotes()
      const refreshedAt = quotes.refreshed_at || new Date().toISOString()
      setLastUpdate(refreshedAt)
      done.push(`题材行情 ${quotes.themes_updated} 个`)
      await refreshMainDashboard()
      publishProgress(strategyPeriodEnabled ? '策略卡' : token ? '短线信号' : null)

      if (strategyPeriodEnabled) {
        if (shortTermPeriod === 'custom' && (!customStartDate || !customEndDate)) {
          skipped.push('策略卡（未选自定义日期）')
          setPeriodStatus({
            type: 'error',
            message: '请先选择自定义日期范围后再刷新策略卡',
          })
        } else {
          try {
            await refreshStrategyDataMutation.mutateAsync(strategyQueryParams)
            done.push('策略卡')
          } catch (strategyError) {
            skipped.push(`策略卡失败：${shortTermErrorMessage(strategyError)}`)
            if (!isCancelledError(strategyError) && !options?.silent) {
              toast.error(`策略卡刷新失败：${shortTermErrorMessage(strategyError)}`)
            }
          }
        }
        publishProgress(token && !options?.silent ? '短线信号' : null)
      }

      // 手动刷新时继续刷短线信号；自动静默刷新跳过，避免每 30 秒打 AkShare
      if (token && !options?.silent) {
        publishProgress('短线信号')
        try {
          const signals = await refreshShortTermSignals()
          await queryClient.invalidateQueries({ queryKey: ['short-term-sectors'] })
          await queryClient.invalidateQueries({ queryKey: ['short-term-overview'] })
          if (signals.status === 'failed') {
            skipped.push(signals.error_message || '短线信号失败')
          } else {
            done.push(
              `短线信号（涨停${signals.signal_count}/龙虎${signals.dragon_tiger_count}/轮动${signals.sector_count}）`
            )
            if (signals.degraded && signals.missing_sources.length > 0) {
              skipped.push(`短线源缺失：${signals.missing_sources.join('、')}`)
            }
          }
        } catch (signalError) {
          skipped.push(`短线信号失败：${shortTermErrorMessage(signalError)}`)
        }
      } else if (!token && !options?.silent) {
        skipped.push('短线信号（未登录）')
      }

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
      setIsDashboardRefreshing(false)
      setUpdateResult({
        type: skipped.length > 0 && done.length === 0 ? 'error' : 'success',
        message: summary,
      })
      if (!options?.silent) {
        if (skipped.length > 0 && done.length > 0) {
          toast.success(`部分刷新完成：${done.join('；')}`)
        } else if (done.length > 0) {
          toast.success(`已刷新：${done.join('；')}`)
        }
      }
    } catch (error) {
      setIsDashboardRefreshing(false)
      lightRefreshPendingRef.current = null
      if (isCancelledError(error)) return
      const message = error instanceof Error ? error.message : '未知错误'
      const partial =
        done.length > 0 ? `已更新：${done.join('；')}。` : ''
      setUpdateResult({
        type: 'error',
        message: `${partial}看板刷新失败：${message}`,
      })
      if (!options?.silent) {
        toast.error(`看板刷新失败：${message}`)
      }
    } finally {
      setIsDashboardRefreshing(false)
      lightRefreshPendingRef.current = null
    }
  }, [
    customEndDate,
    customStartDate,
    queryClient,
    refreshMainDashboard,
    refreshStrategyDataMutation,
    shortTermPeriod,
    strategyPeriodEnabled,
    strategyQueryParams,
    toast,
    token,
  ])

  useEffect(() => {
    if (!isDashboardRefreshing) return
    setUpdateResult((current) => {
      if (current?.type === 'success' || current?.type === 'error') return current
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

  useEffect(() => {
    if (!isUpdating) return
    setUpdateResult({
      type: 'progress',
      message: `正在全量更新（已耗时 ${fullUpdateElapsed}，东方财富慢时将自动切换其他数据源）...`,
    })
  }, [fullUpdateElapsed, isUpdating])

  const updateDashboard = useCallback(async () => {
    const startedAt = Date.now()
    setIsUpdating(true)
    setUpdateResult({
      type: 'progress',
      message: `正在通过${selectedScraperSourceLabel}全量更新（已耗时 0 秒）...`,
    })
    try {
      const sourcesToTry = [
        selectedScraperSource,
        ...dashboardScraperSources
          .map((item) => item.id)
          .filter((id) => id !== selectedScraperSource),
      ]
      const run = await runScraperWithFallback(sourcesToTry)
      if (run.status === 'failed') {
        const message = `全量更新失败：${run.error_message || '未知错误'}`
        setUpdateResult({ type: 'error', message })
        toast.error(message)
        return
      }

      await refreshMainDashboard()
      const finishedAt = run.finished_at ?? new Date().toISOString()
      setLastUpdate(finishedAt)
      queryClient.setQueryData(latestScraperRunQueryKey(run.source), finishedAt)
      await refetchLatestSuccessfulUpdate()
      const usedSourceLabel =
        dashboardScraperSources.find((item) => item.id === run.source)?.label ?? run.source
      const fallbackNote =
        run.attempted_sources.length > 1
          ? `（已自动切换：${run.attempted_sources
              .map(
                (id) => dashboardScraperSources.find((item) => item.id === id)?.label ?? id
              )
              .join(' → ')}）`
          : ''
      const elapsedSeconds = Math.max(1, Math.round((Date.now() - startedAt) / 1000))
      setUpdateResult({
        type: 'success',
        message: `${usedSourceLabel}全量更新成功，共更新 ${run.items_scraped} 条数据，耗时 ${elapsedSeconds} 秒${fallbackNote}`,
      })
      toast.success(`${usedSourceLabel}全量更新成功，共更新 ${run.items_scraped} 条数据`)
    } catch (error) {
      if (isCancelledError(error)) return
      const message = error instanceof Error ? error.message : '未知错误'
      setUpdateResult({ type: 'error', message: `全量更新失败：${message}` })
      toast.error(`全量更新失败：${message}`)
    } finally {
      setIsUpdating(false)
    }
  }, [
    dashboardScraperSources,
    queryClient,
    refreshMainDashboard,
    refetchLatestSuccessfulUpdate,
    selectedScraperSource,
    selectedScraperSourceLabel,
    toast,
  ])

  // 自动刷新：仅在用户打开「自动刷新」后按间隔快刷
  const { isAutoRefresh, toggleAutoRefresh, refreshInterval, setRefreshInterval } = useAutoRefresh({
    interval: 30000, // 默认 30 秒
    onRefresh: () => {
      void handleLightRefresh({ silent: true }).catch((error) => {
        if (!isCancelledError(error)) {
          console.error('自动刷新失败', error)
        }
      })
    },
  })

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
        const endDate =
          databaseStrategyOverview?.end_date ?? dayjs().format('YYYY-MM-DD')
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

  const handleFirstToSecondRefresh = useCallback(async () => {
    setIsFirstToSecondRefreshing(true)
    try {
      await refreshFirstToSecondCandidates({})
      await refetchIgnoringCancel(refetchFirstToSecondCandidates)
      toast.success('一进二候选已实时刷新')
    } catch (error) {
      if (isCancelledError(error)) return
      const message = error instanceof Error ? error.message : '未知错误'
      toast.error(`一进二候选刷新失败：${message}`)
    } finally {
      setIsFirstToSecondRefreshing(false)
    }
  }, [refetchFirstToSecondCandidates, toast])

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
    if (refreshStrategyDataMutation.isPending) {
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
    periodStatus,
    refreshStrategyDataMutation.isPending,
    shortTermDateRange,
    shortTermPeriod,
    strategyRefreshElapsed,
  ])

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
          isFirstToSecondFetching ||
          isUpdating
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
              <AutoRefreshButton
                isRefreshing={isDashboardRefreshing || refreshStrategyDataMutation.isPending}
                isUpdating={isUpdating}
                isAutoRefresh={isAutoRefresh}
                onToggleAutoRefresh={toggleAutoRefresh}
                refreshInterval={refreshInterval}
                onSetRefreshInterval={setRefreshInterval}
                onRefresh={() => void handleLightRefresh()}
                onFullUpdate={() => void updateDashboard()}
                scraperSources={dashboardScraperSources}
                selectedScraperSource={selectedScraperSource}
                onScraperSourceChange={setSelectedScraperSource}
                refreshElapsedLabel={
                  isDashboardRefreshing || refreshStrategyDataMutation.isPending
                    ? dashboardRefreshElapsed || strategyRefreshElapsed
                    : undefined
                }
                updateElapsedLabel={isUpdating ? fullUpdateElapsed : undefined}
              />
              {updateResult && (
                <p
                  className={`text-sm ${
                    updateResult.type === 'error'
                      ? 'text-destructive'
                      : updateResult.type === 'success'
                        ? 'text-primary'
                        : 'text-muted-foreground'
                  }`}
                >
                  {updateResult.message}
                </p>
              )}
            </div>
          }
        />

        <div
          className="mt-6 grid grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(340px,1fr)]"
          data-testid="dashboard-content-grid"
        >
          <div className="min-w-0" data-testid="dashboard-main-column">
            <ShortTermRadarSection
              onFeedback={handleNewsFeedback}
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
                  isPeriodLoading={isStrategyPeriodLoading || isDashboardRefreshing}
                  isPreview={isStrategyPreview}
                  degraded={strategyOverviewForCard.degraded}
                  missingSources={strategyOverviewForCard.missing_sources}
                />
              </div>
            )}

            {/* 涨跌幅、行情指标与市场表现排行 */}
            <div
              className="grid grid-cols-1 gap-6 lg:grid-cols-2 xl:grid-cols-3"
              data-testid="dashboard-ranking-grid"
            >
              <section className="min-w-0">
                <h2 className="mb-4 text-lg font-semibold text-foreground">涨跌幅 Top 20</h2>
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
                <h2 className="mb-3 text-lg font-semibold text-foreground">
                  热门题材 Top {limit}
                </h2>

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
                  isRefreshing={isFirstToSecondRefreshing || isFirstToSecondFetching}
                  onRefresh={() => void handleFirstToSecondRefresh()}
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
