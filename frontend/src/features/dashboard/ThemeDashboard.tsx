/** 题材看板主页面
 *
 * 展示热门题材排名，支持加载、错误和空状态。
 */

import { useQuery } from '@tanstack/react-query'
import { useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchThemeRanking } from '@/api/theme'
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
import { KeyboardShortcutsButton } from '@/components/KeyboardShortcutsPanel'
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts'
import { useAutoRefresh } from '@/hooks/useAutoRefresh'

export function ThemeDashboard() {
  const navigate = useNavigate()
  const limit = useDashboardStore((s) => s.limit)

  const handleThemeClick = useCallback(
    (themeId: number) => navigate(`/themes/${themeId}`),
    [navigate],
  )

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['theme-ranking', limit],
    queryFn: () => fetchThemeRanking(limit),
    staleTime: 2 * 60 * 1000, // 2 分钟
  })

  // 自动刷新
  const {
    isAutoRefresh,
    toggleAutoRefresh,
    refreshInterval,
    setRefreshInterval,
  } = useAutoRefresh({
    interval: 30000, // 默认 30 秒
    onRefresh: () => refetch(),
  })

  // 键盘快捷键
  useKeyboardShortcuts([
    {
      key: 'r',
      action: () => refetch(),
      description: '刷新数据',
    },
    {
      key: 't',
      action: () => navigate('/themes'),
      description: '打开题材库',
    },
  ])

  const themes = data?.items ?? []
  const totalStocks = useMemo(() => themes.reduce((sum, t) => sum + t.stock_count, 0), [themes])

  return (
    <div className="min-h-screen bg-background">
      {/* 加载进度条 */}
      <LoadingBar isLoading={isLoading || isFetching} />

      {/* 页头 */}
      <header className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <h1 className="text-2xl font-bold text-foreground">
            TradingThemesGod <span className="text-muted-foreground font-normal">题材看板</span>
          </h1>
          <div className="flex items-center gap-3">
            <KeyboardShortcutsButton />
            <ThemeToggle />
            <AutoRefreshButton
              isRefreshing={isFetching}
              isAutoRefresh={isAutoRefresh}
              onToggleAutoRefresh={toggleAutoRefresh}
              refreshInterval={refreshInterval}
              onSetRefreshInterval={setRefreshInterval}
              onRefresh={() => refetch()}
            />
          </div>
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
            <ErrorDisplay
              errorType={error?.message?.includes('Network') ? 'network' : 'server'}
              onRetry={() => refetch()}
            />
          )}

          {/* 空状态 */}
          {!isLoading && !isError && themes.length === 0 && (
            <EmptyState type="no-data" />
          )}

          {/* 主题卡片网格 */}
          {!isLoading && !isError && themes.length > 0 && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
              {themes.map((theme) => (
                <ThemeCard
                  key={theme.id}
                  theme={theme}
                  onClick={handleThemeClick}
                />
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
