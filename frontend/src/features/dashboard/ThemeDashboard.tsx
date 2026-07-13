/** 题材看板主页面
 *
 * 展示热门题材排名，支持加载、错误和空状态。
 */

import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { RefreshCw, AlertCircle, Inbox } from 'lucide-react'
import { fetchThemeRanking } from '@/api/theme'
import { useDashboardStore } from '@/stores/dashboard'
import { ThemeCard } from '@/components/ThemeCard'
import { ThemeCardSkeleton } from '@/components/ThemeCardSkeleton'
import { QuickStats } from '@/components/QuickStats'
import { ThemeRiseFallBar } from '@/components/charts/ThemeRiseFallBar'

export function ThemeDashboard() {
  const navigate = useNavigate()
  const limit = useDashboardStore((s) => s.limit)

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['theme-ranking', limit],
    queryFn: () => fetchThemeRanking(limit),
  })

  const themes = data?.items ?? []
  const totalStocks = themes.reduce((sum, t) => sum + t.stock_count, 0)

  return (
    <div className="min-h-screen bg-background">
      {/* 页头 */}
      <header className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <h1 className="text-2xl font-bold text-foreground">
            TradingThemesGod <span className="text-muted-foreground font-normal">题材看板</span>
          </h1>
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
        {/* 快速统计栏 */}
        <QuickStats
          totalThemes={themes.length}
          totalStocks={totalStocks}
          lastUpdate={null}
        />

        {/* 涨跌幅图表 */}
        <section className="mt-6">
          <h2 className="mb-4 text-lg font-semibold text-foreground">
            涨跌幅 Top 10
          </h2>
          <div className="rounded-lg border border-border bg-card p-4">
            {isLoading ? (
              <div className="h-[300px] animate-pulse rounded bg-muted" />
            ) : (
              <ThemeRiseFallBar themes={themes} />
            )}
          </div>
        </section>

        {/* 热门题材区域 */}
        <section className="mt-6">
          <h2 className="mb-4 text-lg font-semibold text-foreground">
            热门题材 Top {limit}
          </h2>

          {/* 加载状态 */}
          {isLoading && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
              {Array.from({ length: limit }).map((_, i) => (
                <ThemeCardSkeleton key={i} />
              ))}
            </div>
          )}

          {/* 错误状态 */}
          {isError && (
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
          )}

          {/* 空状态 */}
          {!isLoading && !isError && themes.length === 0 && (
            <div className="flex flex-col items-center justify-center rounded-lg border border-border bg-card px-6 py-12">
              <Inbox className="h-10 w-10 text-muted-foreground" />
              <p className="mt-3 text-sm text-muted-foreground">
                暂无题材数据
              </p>
            </div>
          )}

          {/* 主题卡片网格 */}
          {!isLoading && !isError && themes.length > 0 && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
              {themes.map((theme) => (
                <ThemeCard
                  key={theme.id}
                  theme={theme}
                  onClick={() => navigate(`/themes/${theme.id}`)}
                />
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
