/** 题材看板主页面
 *
 * 展示热门题材排名，支持加载、错误和空状态。
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import dayjs from 'dayjs'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { List, Settings } from 'lucide-react'
import {
  fetchIndicatorSignals,
  fetchMarketSignals,
  fetchThemeRanking,
  fetchThemes,
} from '@/api/theme'
import {
  analyzeShortTermFromDatabase,
  fetchFirstToSecondCandidates,
  fetchShortTermOverview,
  refreshFirstToSecondCandidates,
  refreshShortTermData,
} from '@/api/short-term'
import { fetchLatestSuccessfulRun, fetchDashboardScraperSources, runScraperAndWait } from '@/api/scraper'
import { useDashboardStore } from '@/stores/dashboard'
import { ThemeCard } from '@/components/ThemeCard'
import { ThemeCardSkeleton } from '@/components/ThemeCardSkeleton'
import { QuickStats } from '@/components/QuickStats'
import { ThemeRiseFallBar } from '@/components/charts/ThemeRiseFallBar'
import { ThemeToggle } from '@/components/ThemeToggle'
import { LoadingBar } from '@/components/LoadingBar'
import { EmptyState } from '@/components/EmptyState'
import { ErrorDisplay } from '@/components/ErrorDisplay'
import { AutoRefreshButton } from '@/components/AutoRefreshButton'
import { AuthNav } from '@/components/AuthNav'
import { KeyboardShortcutsButton } from '@/components/KeyboardShortcutsPanel'
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts'
import { useNavigateToSettings } from '@/hooks/useNavigateToSettings'
import { useAutoRefresh } from '@/hooks/useAutoRefresh'
import { ToastContainer, useToast } from '@/components/Toast'
import { MarketSignalSection } from '@/components/MarketSignalSection'
import { BoardUpgradeReference } from '@/components/BoardUpgradeReference'
import { NewsTimeline } from '@/components/NewsTimeline'
import { MarketStrategyCard } from '@/components/short-term/MarketStrategyCard'
import { GlowCard } from '@/components/GlowCard'
import type { ShortTermOverviewResponse, ShortTermPeriod, ShortTermPeriodStatus } from '@/types/short-term'

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

export function ThemeDashboard() {
  const navigate = useNavigate()
  const navigateToSettings = useNavigateToSettings()
  const queryClient = useQueryClient()
  const limit = useDashboardStore((s) => s.limit)
  const toast = useToast()
  const [isUpdating, setIsUpdating] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<string | null>(null)
  const [updateResult, setUpdateResult] = useState<UpdateResult>(null)
  const [shortTermPeriod, setShortTermPeriod] = useState<ShortTermPeriod>('today')
  const [periodStatus, setPeriodStatus] = useState<ShortTermPeriodStatus | null>(null)
  const [customStartDate, setCustomStartDate] = useState<string | null>(null)
  const [customEndDate, setCustomEndDate] = useState<string | null>(null)
  const [isFirstToSecondRefreshing, setIsFirstToSecondRefreshing] = useState(false)
  const [selectedScraperSource, setSelectedScraperSource] = useState('eastmoney')

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
  const {
    data: shortTermOverview,
    isFetching: isShortTermFetching,
    isError: isShortTermError,
    error: shortTermError,
    refetch: refetchShortTermOverview,
  } = useQuery({
    queryKey: ['short-term-overview', shortTermPeriod, customStartDate, customEndDate],
    queryFn: () =>
      fetchShortTermOverview({
        period: shortTermPeriod,
        ...(shortTermPeriod === 'custom' && customStartDate && customEndDate
          ? { startDate: customStartDate, endDate: customEndDate }
          : {}),
      }),
    enabled: shortTermPeriod !== 'custom' || Boolean(customStartDate && customEndDate),
    placeholderData: (previousData) => previousData,
    staleTime: 2 * 60 * 1000,
  })
  const shortTermQueryParams = useMemo(
    () => ({
      period: shortTermPeriod,
      ...(shortTermPeriod === 'custom' && customStartDate && customEndDate
        ? { startDate: customStartDate, endDate: customEndDate }
        : {}),
    }),
    [shortTermPeriod, customStartDate, customEndDate]
  )
  const shortTermQueryKey = useMemo(
    () => ['short-term-overview', shortTermPeriod, customStartDate, customEndDate] as const,
    [shortTermPeriod, customStartDate, customEndDate]
  )
  const applyShortTermOverview = useCallback(
    (data: ShortTermOverviewResponse) => {
      queryClient.setQueryData(shortTermQueryKey, data)
    },
    [queryClient, shortTermQueryKey]
  )
  const refreshStrategyDataMutation = useMutation({
    mutationFn: () => refreshShortTermData(shortTermQueryParams),
    onMutate: () => {
      setPeriodStatus({ type: 'progress', message: '正在快速刷新题材行情并更新当日快照...' })
    },
    onSuccess: async (data) => {
      applyShortTermOverview(data)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['theme-ranking'] }),
        queryClient.invalidateQueries({ queryKey: ['theme-rise-ranking'] }),
        queryClient.invalidateQueries({ queryKey: ['market-signals'] }),
        queryClient.invalidateQueries({ queryKey: ['indicator-signals'] }),
        queryClient.invalidateQueries({ queryKey: latestScraperRunQueryKey(selectedScraperSource) }),
      ])
      setPeriodStatus({
        type: 'success',
        message: `${SHORT_TERM_PERIOD_LABELS[shortTermPeriod]}行情已刷新，策略卡已更新`,
      })
    },
    onError: (error) => {
      setPeriodStatus({
        type: 'error',
        message: `行情刷新失败：${shortTermErrorMessage(error)}`,
      })
    },
  })
  const analyzeStrategyMutation = useMutation({
    mutationFn: () => analyzeShortTermFromDatabase(shortTermQueryParams),
    onMutate: () => {
      setPeriodStatus({
        type: 'progress',
        message: `正在依据数据库重新分析${SHORT_TERM_PERIOD_LABELS[shortTermPeriod]}策略...`,
      })
    },
    onSuccess: (data) => {
      applyShortTermOverview(data)
      setPeriodStatus({
        type: 'success',
        message: `${SHORT_TERM_PERIOD_LABELS[shortTermPeriod]}策略已按数据库数据重新分析`,
      })
    },
    onError: (error) => {
      setPeriodStatus({
        type: 'error',
        message: `数据库分析失败：${shortTermErrorMessage(error)}`,
      })
    },
  })
  const {
    data: firstToSecondCandidates,
    isLoading: isFirstToSecondLoading,
    isFetching: isFirstToSecondFetching,
    refetch: refetchFirstToSecondCandidates,
  } = useQuery({
    queryKey: ['first-to-second-candidates'],
    queryFn: () => fetchFirstToSecondCandidates({}),
    staleTime: 60 * 1000,
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

  const refreshDashboard = useCallback(async () => {
    await Promise.all([
      refetch({ throwOnError: true }),
      refetchRiseRanking({ throwOnError: true }),
      refetchThemeCount({ throwOnError: true }),
      refetchMarketSignals({ throwOnError: true }),
      refetchIndicatorSignals({ throwOnError: true }),
      refetchShortTermOverview({ throwOnError: true }),
      refetchFirstToSecondCandidates({ throwOnError: true }),
    ])
  }, [
    refetchFirstToSecondCandidates,
    refetch,
    refetchIndicatorSignals,
    refetchMarketSignals,
    refetchRiseRanking,
    refetchShortTermOverview,
    refetchThemeCount,
  ])

  const handleLightRefresh = useCallback(async () => {
    try {
      await refreshDashboard()
      toast.success('看板已刷新')
    } catch (error) {
      const message = error instanceof Error ? error.message : '未知错误'
      toast.error(`看板刷新失败：${message}`)
    }
  }, [refreshDashboard, toast])

  const updateDashboard = useCallback(async () => {
    setIsUpdating(true)
    setUpdateResult({
      type: 'progress',
      message: `正在通过${selectedScraperSourceLabel}全量更新，通常需要较长时间...`,
    })
    try {
      const run = await runScraperAndWait(selectedScraperSource)
      if (run.status === 'failed') {
        const message = `全量更新失败：${run.error_message || '未知错误'}`
        setUpdateResult({ type: 'error', message })
        toast.error(message)
        return
      }

      await refreshDashboard()
      // finished_at 偶发为空时用本地时间兜底，避免更新时间停在旧值
      const finishedAt = run.finished_at ?? new Date().toISOString()
      setLastUpdate(finishedAt)
      queryClient.setQueryData(latestScraperRunQueryKey(selectedScraperSource), finishedAt)
      await refetchLatestSuccessfulUpdate()
      setUpdateResult({
        type: 'success',
        message: `${selectedScraperSourceLabel}全量更新成功，共更新 ${run.items_scraped} 条数据`,
      })
      toast.success(`${selectedScraperSourceLabel}全量更新成功，共更新 ${run.items_scraped} 条数据`)
    } catch (error) {
      const message = error instanceof Error ? error.message : '未知错误'
      setUpdateResult({ type: 'error', message: `全量更新失败：${message}` })
      toast.error(`全量更新失败：${message}`)
    } finally {
      setIsUpdating(false)
    }
  }, [
    queryClient,
    refreshDashboard,
    refetchLatestSuccessfulUpdate,
    selectedScraperSource,
    selectedScraperSourceLabel,
    toast,
  ])

  // 自动刷新
  const { isAutoRefresh, toggleAutoRefresh, refreshInterval, setRefreshInterval } = useAutoRefresh({
    interval: 30000, // 默认 30 秒
    onRefresh: () => void refreshDashboard(),
  })

  // 键盘快捷键
  useKeyboardShortcuts([
    {
      key: 'r',
      action: () => void handleLightRefresh(),
      description: '刷新看板',
    },
    {
      key: 't',
      action: () => navigate('/themes'),
      description: '打开题材库',
    },
  ])

  const themes = useMemo(() => data?.items ?? [], [data?.items])
  const totalStocks = useMemo(() => themes.reduce((sum, t) => sum + t.stock_count, 0), [themes])
  const formattedLastUpdate = useMemo(() => {
    const value = lastUpdate ?? latestSuccessfulUpdate
    return value ? formatServerTime(value) : null
  }, [lastUpdate, latestSuccessfulUpdate])
  const shortTermDateRange = useMemo(() => {
    if (!shortTermOverview) return undefined
    if (shortTermOverview.start_date === shortTermOverview.end_date) {
      return shortTermOverview.end_date
    }
    return `${shortTermOverview.start_date} ~ ${shortTermOverview.end_date}`
  }, [shortTermOverview])

  const handleNewsFeedback = useCallback(
    (type: 'success' | 'error' | 'warning', message: string) => toast[type](message),
    [toast]
  )

  const handleShortTermPeriodChange = useCallback(
    (period: ShortTermPeriod) => {
      if (period === shortTermPeriod) return
      if (period === 'custom') {
        const endDate = shortTermOverview?.end_date ?? dayjs().format('YYYY-MM-DD')
        setCustomEndDate((current) => current ?? endDate)
        setCustomStartDate((current) => current ?? defaultCustomStartDate(endDate))
      }
      setPeriodStatus({
        type: 'progress',
        message: `正在刷新${SHORT_TERM_PERIOD_LABELS[period]}策略数据...`,
      })
      setShortTermPeriod(period)
    },
    [shortTermOverview?.end_date, shortTermPeriod]
  )

  const handleCustomDateRangeChange = useCallback(
    (startDate: string, endDate: string) => {
      setCustomStartDate(startDate)
      setCustomEndDate(endDate)
      if (startDate && endDate) {
        setPeriodStatus({
          type: 'progress',
          message: '正在刷新自定义策略数据...',
        })
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
      await refetchFirstToSecondCandidates({ throwOnError: true })
      toast.success('一进二候选已实时刷新')
    } catch (error) {
      const message = error instanceof Error ? error.message : '未知错误'
      toast.error(`一进二候选刷新失败：${message}`)
    } finally {
      setIsFirstToSecondRefreshing(false)
    }
  }, [refetchFirstToSecondCandidates, toast])

  useEffect(() => {
    if (isShortTermFetching) return

    if (isShortTermError) {
      const message = shortTermError instanceof Error ? shortTermError.message : '未知错误'
      setPeriodStatus({
        type: 'error',
        message: `${SHORT_TERM_PERIOD_LABELS[shortTermPeriod]}策略数据刷新失败：${message}`,
      })
      return
    }

    if (shortTermPeriod !== 'today' && shortTermOverview?.period === shortTermPeriod) {
      setPeriodStatus({
        type: 'success',
        message: `${shortTermOverview.period_label}策略数据已刷新`,
      })
    }
  }, [
    isShortTermError,
    isShortTermFetching,
    shortTermError,
    shortTermOverview,
    shortTermPeriod,
  ])
  const visiblePeriodStatus = useMemo<ShortTermPeriodStatus | null>(() => {
    if (isShortTermFetching) {
      return {
        type: 'progress',
        message: `正在刷新${SHORT_TERM_PERIOD_LABELS[shortTermPeriod]}策略数据...`,
      }
    }
    return periodStatus
  }, [isShortTermFetching, periodStatus, shortTermPeriod])

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
          isShortTermFetching ||
          isFirstToSecondFetching ||
          isUpdating
        }
      />

      {/* 页头 */}
      <header className="sticky top-3 z-20 mx-3 mt-3 rounded-xl border border-border/60 bg-background/80 shadow-lg shadow-black/5 backdrop-blur-md sm:mx-4 sm:mt-4">
        <div
          className="mx-auto flex w-full max-w-none flex-wrap items-center justify-between gap-3 px-3 py-4 sm:px-4 lg:px-5 xl:px-6"
          data-testid="dashboard-header-shell"
        >
          <h1>
            <button
              type="button"
              aria-label="返回主页"
              onClick={() => navigate('/')}
              className="text-left text-xl font-bold text-foreground transition-colors hover:text-primary sm:text-2xl"
            >
              TradingThemesGod <span className="text-muted-foreground font-normal">题材看板</span>
            </button>
          </h1>
          <div className="flex flex-wrap items-center justify-end gap-2 sm:gap-3">
            <button
              type="button"
              onClick={() => navigate('/themes')}
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              <List className="h-4 w-4" />
              <span>题材库</span>
            </button>
            <button
              type="button"
              onClick={navigateToSettings}
              className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-3 py-2 text-sm font-medium text-card-foreground transition-colors hover:bg-accent"
            >
              <Settings className="h-4 w-4" />
              <span>模型设置</span>
            </button>
            <KeyboardShortcutsButton />
            <AuthNav />
            <ThemeToggle />
          </div>
        </div>
      </header>

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
                isRefreshing={
                  isFetching ||
                  isRiseRankingFetching ||
                  isThemeCountFetching ||
                  isMarketSignalsFetching ||
                  isIndicatorSignalsFetching
                }
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
            {shortTermOverview?.strategy_card && (
              <div className="mb-6">
                <MarketStrategyCard
                  card={shortTermOverview.strategy_card}
                  period={shortTermPeriod}
                  periodLabel={shortTermOverview.period_label}
                  dateRange={shortTermDateRange}
                  onPeriodChange={handleShortTermPeriodChange}
                  customStartDate={customStartDate ?? undefined}
                  customEndDate={customEndDate ?? undefined}
                  onCustomDateRangeChange={handleCustomDateRangeChange}
                  periodStatus={visiblePeriodStatus}
                  degraded={shortTermOverview.degraded}
                  missingSources={shortTermOverview.missing_sources}
                  isRefreshingData={refreshStrategyDataMutation.isPending}
                  isAnalyzingDatabase={analyzeStrategyMutation.isPending}
                  onRefreshData={() => {
                    if (shortTermPeriod === 'custom' && (!customStartDate || !customEndDate)) {
                      setPeriodStatus({
                        type: 'error',
                        message: '请先选择自定义日期范围',
                      })
                      return
                    }
                    refreshStrategyDataMutation.mutate()
                  }}
                  onAnalyzeDatabase={() => {
                    if (shortTermPeriod === 'custom' && (!customStartDate || !customEndDate)) {
                      setPeriodStatus({
                        type: 'error',
                        message: '请先选择自定义日期范围',
                      })
                      return
                    }
                    analyzeStrategyMutation.mutate()
                  }}
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
