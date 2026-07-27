/** 题材详情页主组件
 *
 * 展示题材详细信息和产业链结构。
 * 路由，themes/:id
 */

import { useMemo } from 'react'
import { useLocation, useParams, useNavigate } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import dayjs from 'dayjs'
import {
  RefreshCw,
  AlertCircle,
  Inbox,
  ArrowLeft,
  Flame,
  TrendingUp,
  TrendingDown,
  Minus,
  Tag,
  Layers,
} from 'lucide-react'
import { fetchThemeDetail, refreshConceptGraph, refreshThemeInsights } from '@/api/theme'
import { getHeatColor, getRiseFallColor } from '@/lib/theme-colors'
import { IndustryChainSection } from '@/components/IndustryChainSection'
import { ThemeConstituentStocks } from '@/components/ThemeConstituentStocks'
import { ConceptGraphSection } from '@/components/ConceptGraphSection'
import { Skeleton } from '@/components/ui/skeleton'
import { ThemeHeatTrendLine, type HeatTrendDataPoint } from '@/components/charts/ThemeHeatTrendLine'
import { IndustryChainPie } from '@/components/charts/IndustryChainPie'
import { formatRiseFall } from '@/lib/utils'
import { ThemeMarketBreadth } from '@/components/ThemeMarketBreadth'
import { ThemeProfileSection } from '@/components/ThemeProfileSection'
import { ThemeDriverEvents } from '@/components/ThemeDriverEvents'
import { GlowCard } from '@/components/GlowCard'
import { AppCardNav } from '@/components/AppCardNav'
import { ThemeLifecycleBadge } from '@/components/ThemeLifecycleBadge'
import { ThemeStrengthGauge } from '@/components/ThemeStrengthGauge'
import { ThemeLifecycleTrend } from '@/components/charts/ThemeLifecycleTrend'
import { useNavigateToSettings } from '@/hooks/useNavigateToSettings'
import { formatRefreshDurationMs, useRefreshTimer } from '@/hooks/useRefreshTimer'

function formatServerTime(value: string): string {
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)
  return dayjs(hasTimezone ? value : `${value}Z`).format('YYYY-MM-DD HH:mm:ss')
}

/**
 * 生成模拟热度趋势数据
 *
 * 基于当前热度指数生成最返7 天的趋势数据。
 * TODO: 接入后端热度趋势 API 替换此函数
 */
function generateMockHeatTrend(currentHeat: number): HeatTrendDataPoint[] {
  const points: HeatTrendDataPoint[] = []
  const now = new Date()

  for (let i = 6; i >= 0; i--) {
    const date = new Date(now)
    date.setDate(date.getDate() - i)

    // 生成波动范围 ±15% 的模拟数据
    const variation = (Math.random() - 0.5) * 0.3 * currentHeat
    const value = Math.max(0, currentHeat + variation)

    points.push({
      date: date.toISOString().split('T')[0],
      value: Math.round(value * 10) / 10,
    })
  }

  return points
}

export function ThemeDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const navigateToSettings = useNavigateToSettings()
  const location = useLocation()
  const themeId = Number(id)
  const returnPath =
    typeof location.state?.from === 'string' && location.state.from.startsWith('/')
      ? location.state.from
      : '/themes'
  const handleBack = () => navigate(returnPath)

  const {
    data: theme,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['theme-detail', themeId],
    queryFn: () => fetchThemeDetail(themeId),
    enabled: !isNaN(themeId),
    staleTime: 3 * 60 * 1000, // 3 分钟
  })
  const heatValue = Number(theme?.heat_index ?? 0)
  const mockHeatTrend = useMemo(() => generateMockHeatTrend(heatValue), [heatValue])
  const graphRefresh = useMutation({
    mutationFn: () => refreshConceptGraph(themeId),
    onSuccess: () => refetch(),
  })
  const insightRefresh = useMutation({
    mutationFn: () => refreshThemeInsights(themeId),
    onSuccess: () => refetch(),
  })
  const { elapsedLabel: graphElapsed } = useRefreshTimer(graphRefresh.isPending)
  const { elapsedLabel: insightElapsed } = useRefreshTimer(insightRefresh.isPending)
  const refreshError = graphRefresh.error as {
    response?: { status?: number; data?: { detail?: string; message?: string } }
    message?: string
  } | null
  const insightRefreshError = insightRefresh.error as {
    response?: { data?: { detail?: string; message?: string } }
    message?: string
  } | null
  const graphErrorMessage =
    refreshError?.response?.data?.detail ||
    refreshError?.response?.data?.message ||
    refreshError?.message ||
    '图谱刷新失败，原图谱已保留'
  const insightErrorMessage =
    insightRefreshError?.response?.data?.detail ||
    insightRefreshError?.response?.data?.message ||
    insightRefreshError?.message ||
    '题材资料刷新失败，已保留原有数据'
  // 加载状态
  if (isLoading) {
    return (
      <div className="min-h-screen">
        <AppCardNav />
        <main className="mx-auto w-full max-w-none px-3 py-6 sm:px-4 lg:px-5 xl:px-6">
          <div className="space-y-6">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        </main>
      </div>
    )
  }

  // 错误状态
  if (isError) {
    return (
      <div className="min-h-screen">
        <AppCardNav />
        <main className="mx-auto w-full max-w-none px-3 py-6 sm:px-4 lg:px-5 xl:px-6">
          <div className="flex flex-col items-center justify-center rounded-xl border border-destructive/30 bg-destructive/5 px-6 py-12">
            <AlertCircle className="h-10 w-10 text-destructive" />
            <p className="mt-3 text-sm text-destructive">
              加载失败：{error?.message ?? '未知错误'}
            </p>
            <button
              onClick={() => refetch()}
              className="mt-4 inline-flex items-center gap-2 rounded-xl bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground hover:bg-destructive/90"
            >
              <RefreshCw className="h-4 w-4" />
              重试
            </button>
          </div>
        </main>
      </div>
    )
  }

  // 空状态
  if (!theme) {
    return (
      <div className="min-h-screen">
        <AppCardNav />
        <main className="mx-auto w-full max-w-none px-3 py-6 sm:px-4 lg:px-5 xl:px-6">
          <div className="flex flex-col items-center justify-center rounded-xl border border-border bg-card px-6 py-12">
            <Inbox className="h-10 w-10 text-muted-foreground" />
            <p className="mt-3 text-sm text-muted-foreground">题材不存在</p>
            <button onClick={handleBack} className="mt-3 text-sm text-primary hover:underline">
              返回题材库
            </button>
          </div>
        </main>
      </div>
    )
  }

  const riseFallValue = Number(theme.rise_fall_pct)
  const heatColor = getHeatColor(heatValue)
  const riseFallColor = getRiseFallColor(riseFallValue)
  const tags = Array.isArray(theme.tags) ? theme.tags : []
  const hasLegacyChainData = Object.values(theme.chain_stock_counts).some((count) => count > 0)

  return (
    <div className="min-h-screen">
      <AppCardNav />

      <header className="mx-auto w-full max-w-none px-3 pt-4 sm:px-4 lg:px-5 xl:px-6">
        <div
          data-testid="theme-detail-header"
          className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between"
        >
          <div className="flex min-w-0 items-center gap-4">
            <button
              onClick={handleBack}
              className="rounded-xl p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              aria-label="返回"
            >
              <ArrowLeft className="h-5 w-5" />
            </button>
            <h1 className="min-w-0 break-words text-xl font-bold text-foreground">{theme.name}</h1>
          </div>
          <div className="grid w-full grid-cols-1 gap-2 min-[360px]:grid-cols-2 sm:flex sm:w-auto sm:flex-wrap sm:items-center sm:justify-end">
            <button
              onClick={() => insightRefresh.mutate()}
              disabled={isFetching || insightRefresh.isPending || graphRefresh.isPending}
              className="inline-flex min-w-0 items-center justify-center gap-2 rounded-xl bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-opacity disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${insightRefresh.isPending ? 'animate-spin' : ''}`} />
              {insightRefresh.isPending
                ? `正在研究（已耗时 ${insightElapsed}）`
                : '刷新题材资料'}
            </button>
            <button
              onClick={() => graphRefresh.mutate()}
              disabled={isFetching || graphRefresh.isPending || insightRefresh.isPending}
              className="inline-flex min-w-0 items-center justify-center gap-2 rounded-xl border border-border bg-card px-3 py-2 text-sm font-medium text-card-foreground transition-colors hover:bg-accent disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${graphRefresh.isPending ? 'animate-spin' : ''}`} />
              {graphRefresh.isPending ? `正在分析（已耗时 ${graphElapsed}）` : '刷新图谱'}
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-none px-3 py-6 sm:px-4 lg:px-5 xl:px-6">
        {graphRefresh.isPending && (
          <div
            role="status"
            className="mb-5 rounded-xl border border-primary/30 bg-primary/5 px-4 py-3 text-sm text-muted-foreground"
          >
            正在刷新图谱（已耗时 {graphElapsed}）…
          </div>
        )}
        {graphRefresh.data && !graphRefresh.isPending && (
          <div
            role="status"
            className="mb-5 flex flex-wrap gap-x-5 gap-y-1 rounded-xl border border-primary/30 bg-primary/5 px-4 py-3 text-sm"
          >
            <span>{graphRefresh.data.message}</span>
            <span>更新于 {formatServerTime(graphRefresh.data.refreshed_at)}</span>
            <span>耗时 {formatRefreshDurationMs(graphRefresh.data.elapsed_ms)}</span>
            <span>来源 {graphRefresh.data.source_count}</span>
            <span>新增 {graphRefresh.data.added_nodes}</span>
            <span>更新 {graphRefresh.data.updated_nodes}</span>
            <span>股票关联 {graphRefresh.data.stock_links}</span>
          </div>
        )}
        {refreshError && (
          <div
            role="alert"
            className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
          >
            <span>{graphErrorMessage}</span>
            {refreshError.response?.status === 401 ? (
              <button
                onClick={() => navigate('/login', { state: { from: location.pathname } })}
                className="rounded-xl border border-current px-3 py-1.5 font-medium"
              >
                去登录
              </button>
            ) : refreshError.response?.status === 409 ? (
              <button
                onClick={navigateToSettings}
                className="rounded-xl border border-current px-3 py-1.5 font-medium"
              >
                前往模型设置
              </button>
            ) : null}
          </div>
        )}
        {/* 题材头部信息 */}
        <GlowCard>
        <section className="p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            {/* 左侧：名称和描述 */}
            <div className="flex-1">
              <div className="flex items-center gap-3">
                <h2 className="text-2xl font-bold text-foreground">{theme.name}</h2>
                {theme.category && (
                  <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
                    {theme.category}
                  </span>
                )}
              </div>
              {theme.description && (
                <p className="mt-2 text-sm text-muted-foreground">{theme.description}</p>
              )}
              {tags.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {tags.map((tag, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center gap-1 rounded-xl bg-muted px-2 py-0.5 text-xs text-muted-foreground"
                    >
                      <Tag className="h-3 w-3" />
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* 右侧：统计数据*/}
            <div className="flex gap-4 sm:gap-6">
              {/* 热度指数 */}
              <div className="text-center">
                <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  <Flame className="h-4 w-4" />
                  <span>热度</span>
                </div>
                <div className={`mt-1 rounded-xl px-2.5 py-1 text-lg font-bold ${heatColor}`}>
                  {heatValue.toFixed(1)}
                </div>
              </div>

              {/* 涨跌幅*/}
              <div className="text-center">
                <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  {riseFallValue > 0 && <TrendingUp className="h-4 w-4" />}
                  {riseFallValue < 0 && <TrendingDown className="h-4 w-4" />}
                  {riseFallValue === 0 && <Minus className="h-4 w-4" />}
                  <span>涨跌幅</span>
                </div>
                <div className={`mt-1 text-lg font-bold ${riseFallColor}`}>
                  {formatRiseFall(riseFallValue)}
                </div>
              </div>

              {/* 股票数量 */}
              <div className="text-center">
                <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  <Layers className="h-4 w-4" />
                  <span>股票</span>
                </div>
                <div className="mt-1 text-lg font-bold text-foreground">{theme.stock_count}</div>
              </div>
            </div>
          </div>
        </section>
        </GlowCard>

        {insightRefresh.isPending && (
          <div
            role="status"
            className="mt-5 rounded-xl border border-primary/30 bg-primary/5 px-4 py-3 text-sm text-muted-foreground"
          >
            <p>正在刷新题材资料（已耗时 {insightElapsed}）…</p>
            <p className="mt-1 text-xs">
              流程：抓取公开网页/资讯 → 调用默认模型整理档案与事件。若超过数分钟仍无结果，多半卡在网页抓取或模型超时；可刷新页面后重试。
            </p>
          </div>
        )}
        {insightRefresh.data && !insightRefresh.isPending && (
          <div
            role="status"
            className="mt-5 space-y-3 rounded-xl border border-primary/30 bg-primary/5 px-4 py-3 text-sm"
            data-testid="insight-refresh-result"
          >
            <p>
              {insightRefresh.data.message}，新增事件 {insightRefresh.data.inserted_events}{' '}
              条，来源 {insightRefresh.data.source_count ?? insightRefresh.data.successful_sources.length}{' '}
              条，更新于 {formatServerTime(insightRefresh.data.refreshed_at)}，耗时{' '}
              {formatRefreshDurationMs(insightRefresh.data.elapsed_ms)}
            </p>
            {insightRefresh.data.failed_sources.length > 0 && (
              <p className="text-muted-foreground">
                失败来源：{insightRefresh.data.failed_sources.join('、')}
              </p>
            )}
            {(insightRefresh.data.model_name ||
              insightRefresh.data.model_error ||
              insightRefresh.data.model_reasoning ||
              insightRefresh.data.model_raw_response) && (
              <details className="rounded-lg border border-border/60 bg-background/40 px-3 py-2" open>
                <summary className="cursor-pointer text-xs font-medium text-foreground">
                  模型调用详情
                  {insightRefresh.data.model_name ? ` · ${insightRefresh.data.model_name}` : ''}
                  {insightRefresh.data.degraded ? ' · 已降级' : ''}
                </summary>
                <div className="mt-2 space-y-2 text-xs text-muted-foreground">
                  {insightRefresh.data.model_error && (
                    <div>
                      <div className="mb-1 font-medium text-destructive">错误</div>
                      <pre className="max-h-40 overflow-auto whitespace-pre-wrap break-all rounded-md bg-destructive/5 p-2 text-destructive">
                        {insightRefresh.data.model_error}
                      </pre>
                    </div>
                  )}
                  {insightRefresh.data.model_reasoning && (
                    <div>
                      <div className="mb-1 font-medium text-foreground">思考过程</div>
                      <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-words rounded-md bg-muted/40 p-2 text-foreground/90">
                        {insightRefresh.data.model_reasoning}
                      </pre>
                    </div>
                  )}
                  {insightRefresh.data.model_raw_response && (
                    <div>
                      <div className="mb-1 font-medium text-foreground">原始返回（截断）</div>
                      <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-all rounded-md bg-muted/40 p-2 text-foreground/80">
                        {insightRefresh.data.model_raw_response}
                      </pre>
                    </div>
                  )}
                </div>
              </details>
            )}
          </div>
        )}
        {insightRefresh.isError && (
          <div
            role="alert"
            className="mt-5 rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive"
          >
            {insightErrorMessage}
          </div>
        )}
        <div
          data-testid="theme-detail-content-grid"
          className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]"
        >
          <div className="min-w-0">
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <ThemeLifecycleBadge stage={theme.lifecycle_stage} />
              {typeof theme.lifecycle_confidence === 'number' && (
                <span className="text-xs text-muted-foreground">
                  置信 {theme.lifecycle_confidence}
                </span>
              )}
            </div>
            <ThemeMarketBreadth snapshot={theme.market_snapshot} />
            <ThemeProfileSection profile={theme.profile} className="mt-6" />

            {/* 图表区域 */}
            <section
              className={`mt-6 grid grid-cols-1 gap-6 ${hasLegacyChainData ? 'lg:grid-cols-2' : ''}`}
            >
              {/* 热度趋势折线图*/}
              <GlowCard>
              <div className="p-4">
                <h3 className="mb-2 text-sm font-medium text-muted-foreground">热度趋势</h3>
                <ThemeHeatTrendLine data={mockHeatTrend} />
              </div>
              </GlowCard>

              {/* 产业链分布饼图*/}
              {hasLegacyChainData && (
                <GlowCard>
                <div className="p-4">
                  <h3 className="mb-2 text-sm font-medium text-muted-foreground">产业链分布</h3>
                  <IndustryChainPie
                    chains={theme.industry_chains}
                    stockCounts={theme.chain_stock_counts}
                  />
                </div>
                </GlowCard>
              )}
            </section>

            <section className="mt-6 border-y border-border py-6">
              <ConceptGraphSection graph={theme.concept_graph} />
            </section>

            {/* 全部成分股，不依赖产业链数据 */}
            <section className="mt-6 border-y border-border py-6">
              <ThemeConstituentStocks themeId={theme.id} />
            </section>

            {/* 产业链区域*/}
            {hasLegacyChainData && (
              <section className="mt-6">
                <IndustryChainSection chains={theme.industry_chains} themeId={theme.id} />
              </section>
            )}
          </div>

          <aside
            data-testid="theme-detail-side-rail"
            className="min-w-0 space-y-4 xl:sticky xl:top-24 xl:self-start"
          >
            <ThemeStrengthGauge
              strengthScore={theme.strength_score}
              limitQualityScore={theme.limit_quality_score}
              flowScore={theme.flow_score}
              leaderClarityScore={theme.leader_clarity_score}
              breadthScore={theme.breadth_score}
            />
            <GlowCard>
              <div className="p-3">
                <ThemeLifecycleTrend themeId={theme.id} />
              </div>
            </GlowCard>
            <ThemeDriverEvents events={theme.recent_driver_events} />
          </aside>
        </div>
      </main>
    </div>
  )
}
