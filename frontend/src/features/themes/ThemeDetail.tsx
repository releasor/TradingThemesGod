/** 题材详情页主组件
 *
 * 展示题材详细信息和产业链结构。
 * 路由：/themes/:id
 */

import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
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
import { fetchThemeDetail } from '@/api/theme'
import { getHeatColor, getRiseFallColor } from '@/lib/theme-colors'
import { IndustryChainSection } from '@/components/IndustryChainSection'
import { Skeleton } from '@/components/ui/skeleton'
import { ThemeHeatTrendLine, type HeatTrendDataPoint } from '@/components/charts/ThemeHeatTrendLine'
import { IndustryChainPie } from '@/components/charts/IndustryChainPie'
import { formatRiseFall } from '@/lib/utils'

/**
 * 生成模拟热度趋势数据
 *
 * 基于当前热度指数生成最近 7 天的趋势数据。
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
  const themeId = Number(id)

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
  })

  // 加载状态
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background">
        <header className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur">
          <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-4 sm:px-6 lg:px-8">
            <Skeleton className="h-8 w-8" />
            <Skeleton className="h-7 w-48" />
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
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
      <div className="min-h-screen bg-background">
        <header className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur">
          <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-4 sm:px-6 lg:px-8">
            <button
              onClick={() => navigate('/themes')}
              className="rounded-md p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            >
              <ArrowLeft className="h-5 w-5" />
            </button>
            <h1 className="text-xl font-bold text-foreground">题材详情</h1>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex flex-col items-center justify-center rounded-lg border border-destructive/30 bg-destructive/5 px-6 py-12">
            <AlertCircle className="h-10 w-10 text-destructive" />
            <p className="mt-3 text-sm text-destructive">
              加载失败：{error?.message ?? '未知错误'}
            </p>
            <button
              onClick={() => refetch()}
              className="mt-4 inline-flex items-center gap-2 rounded-md bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground hover:bg-destructive/90"
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
      <div className="min-h-screen bg-background">
        <header className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur">
          <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-4 sm:px-6 lg:px-8">
            <button
              onClick={() => navigate('/themes')}
              className="rounded-md p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            >
              <ArrowLeft className="h-5 w-5" />
            </button>
            <h1 className="text-xl font-bold text-foreground">题材详情</h1>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex flex-col items-center justify-center rounded-lg border border-border bg-card px-6 py-12">
            <Inbox className="h-10 w-10 text-muted-foreground" />
            <p className="mt-3 text-sm text-muted-foreground">题材不存在</p>
            <button
              onClick={() => navigate('/themes')}
              className="mt-3 text-sm text-primary hover:underline"
            >
              返回题材库
            </button>
          </div>
        </main>
      </div>
    )
  }

  const heatColor = getHeatColor(Number(theme.heat_index))
  const riseFallColor = getRiseFallColor(Number(theme.rise_fall_pct))
  const tags = Array.isArray(theme.tags) ? theme.tags : []

  return (
    <div className="min-h-screen bg-background">
      {/* 页头 */}
      <header className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/themes')}
              className="rounded-md p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            >
              <ArrowLeft className="h-5 w-5" />
            </button>
            <h1 className="text-xl font-bold text-foreground">{theme.name}</h1>
          </div>
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="inline-flex items-center gap-2 rounded-md border border-border bg-card px-3 py-2 text-sm font-medium text-card-foreground transition-colors hover:bg-accent disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
            刷新
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        {/* 题材头部信息 */}
        <section className="rounded-lg border border-border bg-card p-6">
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
                <p className="mt-2 text-sm text-muted-foreground">
                  {theme.description}
                </p>
              )}
              {tags.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {tags.map((tag, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center gap-1 rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground"
                    >
                      <Tag className="h-3 w-3" />
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* 右侧：统计数据 */}
            <div className="flex gap-4 sm:gap-6">
              {/* 热度指数 */}
              <div className="text-center">
                <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  <Flame className="h-4 w-4" />
                  <span>热度</span>
                </div>
                <div
                  className={`mt-1 rounded-md px-2.5 py-1 text-lg font-bold ${heatColor}`}
                >
                  {Number(theme.heat_index).toFixed(1)}
                </div>
              </div>

              {/* 涨跌幅 */}
              <div className="text-center">
                <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  {Number(theme.rise_fall_pct) > 0 && (
                    <TrendingUp className="h-4 w-4" />
                  )}
                  {Number(theme.rise_fall_pct) < 0 && (
                    <TrendingDown className="h-4 w-4" />
                  )}
                  {Number(theme.rise_fall_pct) === 0 && (
                    <Minus className="h-4 w-4" />
                  )}
                  <span>涨跌幅</span>
                </div>
                <div
                  className={`mt-1 text-lg font-bold ${riseFallColor}`}
                >
                  {formatRiseFall(Number(theme.rise_fall_pct))}
                </div>
              </div>

              {/* 股票数量 */}
              <div className="text-center">
                <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  <Layers className="h-4 w-4" />
                  <span>股票</span>
                </div>
                <div className="mt-1 text-lg font-bold text-foreground">
                  {theme.stock_count}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* 图表区域 */}
        <section className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* 热度趋势折线图 */}
          <div className="rounded-lg border border-border bg-card p-4">
            <h3 className="mb-2 text-sm font-medium text-muted-foreground">热度趋势</h3>
            <ThemeHeatTrendLine data={generateMockHeatTrend(Number(theme.heat_index))} />
          </div>

          {/* 产业链分布饼图 */}
          <div className="rounded-lg border border-border bg-card p-4">
            <h3 className="mb-2 text-sm font-medium text-muted-foreground">产业链分布</h3>
            <IndustryChainPie chains={theme.industry_chains} />
          </div>
        </section>

        {/* 产业链区域 */}
        <section className="mt-6">
          <IndustryChainSection
            chains={theme.industry_chains}
            themeId={theme.id}
          />
        </section>
      </main>
    </div>
  )
}
