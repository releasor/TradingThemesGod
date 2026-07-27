/** 题材库主页面
 *
 * 浏览所有题材，支持搜索、筛选、排序和分页。
 * 筛选状态同步到 URL search params，支持分享。
 */

import { useCallback, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useLocation, useNavigate } from 'react-router-dom'
import { RefreshCw, AlertCircle, Inbox, List, Sparkles } from 'lucide-react'
import { fetchThemes, fetchCategories, refreshConceptGraph } from '@/api/theme'
import type { ConceptGraphRefreshResponse } from '@/types/theme'
import { useThemeFilters } from '@/hooks/useThemeFilters'
import { FilterBar } from '@/components/FilterBar'
import { AppCardNav } from '@/components/AppCardNav'
import { SortSelect } from '@/components/SortSelect'
import { ExportButton } from '@/components/ExportButton'
import { ThemeTableRow } from '@/components/ThemeTableRow'
import { ThemeTableSkeleton } from '@/components/ThemeTableSkeleton'
import { Pagination } from '@/components/Pagination'
import { useNavigateToSettings } from '@/hooks/useNavigateToSettings'

interface BatchProgressItem {
  themeId: number
  themeName: string
  status: 'pending' | 'running' | 'success' | 'error'
  result?: ConceptGraphRefreshResponse
  error?: string
}

function getErrorMessage(error: unknown): string {
  const value = error as {
    response?: { data?: { detail?: string; message?: string } }
    message?: string
  }
  return (
    value.response?.data?.detail ||
    value.response?.data?.message ||
    value.message ||
    '图谱更新失败'
  )
}

function getPreservedGraphMessage(message: string): string {
  return message.includes('已保留') ? message : `${message}；已有图谱已保留`
}

export function ThemeLibrary() {
  const navigate = useNavigate()
  const navigateToSettings = useNavigateToSettings()
  const location = useLocation()
  const [batchItems, setBatchItems] = useState<BatchProgressItem[]>([])
  const [currentBatchIndex, setCurrentBatchIndex] = useState<number | null>(null)
  const [isBatchUpdating, setIsBatchUpdating] = useState(false)
  const [lifecycleFilter, setLifecycleFilter] = useState<string>('')
  const {
    filters,
    searchInput,
    setSearchInput,
    updateFilter,
    setPage,
    setSort,
    clearFilters,
    activeFilterCount,
  } = useThemeFilters()

  const handleThemeClick = useCallback(
    (themeId: number) =>
      navigate(`/themes/${themeId}`, {
        state: { from: `${location.pathname}${location.search}` },
      }),
    [location.pathname, location.search, navigate]
  )

  // 稳定化传组FilterBar 的回调，避免 memo 失效
  const handleSearchChange = useCallback((value: string) => setSearchInput(value), [setSearchInput])
  const handleCategoryChange = useCallback(
    (value: string | undefined) => updateFilter('category', value),
    [updateFilter]
  )
  const handleTagsChange = useCallback(
    (value: string | undefined) => updateFilter('tags', value),
    [updateFilter]
  )
  const handleClearFilters = useCallback(() => clearFilters(), [clearFilters])

  // 获取题材列表
  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['themes', filters],
    queryFn: ({ signal }) => fetchThemes(filters, signal),
  })

  // 获取分类列表（缓存较长时间）
  const { data: categoriesData } = useQuery({
    queryKey: ['theme-categories'],
    queryFn: fetchCategories,
    staleTime: 10 * 60 * 1000, // 10 分钟
  })

  const themes = useMemo(() => {
    const items = data?.items ?? []
    if (!lifecycleFilter) return items
    return items.filter((theme) => theme.lifecycle_stage === lifecycleFilter)
  }, [data?.items, lifecycleFilter])
  const total = data?.total ?? 0
  const totalPages = data?.total_pages ?? 0
  const categories = categoriesData?.categories ?? []
  const successfulBatchCount = batchItems.filter((item) => item.status === 'success').length
  const failedBatchCount = batchItems.filter((item) => item.status === 'error').length
  const isBatchComplete =
    batchItems.length > 0 && batchItems.every((item) => ['success', 'error'].includes(item.status))

  const handleBatchRefresh = useCallback(async () => {
    const targets = themes.slice(0, 5)
    if (!targets.length || isBatchUpdating) return

    setBatchItems(
      targets.map((theme) => ({
        themeId: theme.id,
        themeName: theme.name,
        status: 'pending',
      }))
    )
    setIsBatchUpdating(true)

    for (const [index, theme] of targets.entries()) {
      setCurrentBatchIndex(index)
      setBatchItems((items) =>
        items.map((item, itemIndex) =>
          itemIndex === index ? { ...item, status: 'running' } : item
        )
      )

      try {
        const result = await refreshConceptGraph(theme.id)
        setBatchItems((items) =>
          items.map((item, itemIndex) =>
            itemIndex === index ? { ...item, status: 'success', result } : item
          )
        )
      } catch (error) {
        setBatchItems((items) =>
          items.map((item, itemIndex) =>
            itemIndex === index ? { ...item, status: 'error', error: getErrorMessage(error) } : item
          )
        )
      }
    }

    setCurrentBatchIndex(null)
    setIsBatchUpdating(false)
  }, [isBatchUpdating, themes])

  return (
    <div className="min-h-screen">
      <AppCardNav />

      <div className="mx-auto flex w-full max-w-none flex-wrap items-center justify-between gap-3 px-3 pt-4 sm:px-4 lg:px-5 xl:px-6">
        <h1 className="text-lg font-semibold text-foreground">
          题材库
          <span className="ml-2 text-sm font-normal text-muted-foreground">浏览与筛选全部题材</span>
        </h1>
        <div className="flex flex-wrap items-center gap-2">
          <ExportButton
            data={themes.map((theme) => ({
              ...theme,
              category: theme.category ?? undefined,
            }))}
          />
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-3 py-2 text-sm font-medium text-card-foreground transition-colors hover:bg-accent disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
            刷新
          </button>
        </div>
      </div>

      <main className="mx-auto w-full max-w-none px-3 py-6 sm:px-4 lg:px-5 xl:px-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
          <div>
            <h2 className="text-base font-semibold">题材细分图谱</h2>
            <p className="text-sm text-muted-foreground">按当前页题材抓取公开资料并增量分析。</p>
          </div>
          <button
            type="button"
            onClick={() => void handleBatchRefresh()}
            disabled={!themes.length || isBatchUpdating}
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-3 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
          >
            <Sparkles className={`h-4 w-4 ${isBatchUpdating ? 'animate-pulse' : ''}`} />
            {isBatchUpdating && currentBatchIndex !== null
              ? `正在更新 ${currentBatchIndex + 1}/${batchItems.length}`
              : '更新本页前 5 个图谱'}
          </button>
          {isBatchUpdating && currentBatchIndex !== null && (
            <p role="status" className="w-full text-sm font-medium text-foreground">
              正在分析：{batchItems[currentBatchIndex]?.themeName}
            </p>
          )}
          {isBatchComplete && (
            <p role="status" className="w-full text-sm font-medium text-foreground">
              更新完成：成功 {successfulBatchCount} 个，失败 {failedBatchCount} 个
            </p>
          )}
          {batchItems.length > 0 && (
            <div className="w-full divide-y divide-border border-y border-border" aria-label="图谱更新结果">
              {batchItems.map((item) => (
                <div key={item.themeId} className="flex flex-col gap-1 py-3 text-sm sm:flex-row sm:items-start sm:justify-between sm:gap-4">
                  <span className="font-medium text-foreground">{item.themeName}</span>
                  <div className="min-w-0 sm:text-right">
                    {item.status === 'pending' && <span className="text-muted-foreground">等待更新</span>}
                    {item.status === 'running' && <span className="text-primary">正在抓取和分析</span>}
                    {item.status === 'success' && item.result && (
                      <span className="text-muted-foreground">
                        来源 {item.result.source_count}，新增 {item.result.added_nodes}，更新{' '}
                        {item.result.updated_nodes}，股票关联 {item.result.stock_links}
                      </span>
                    )}
                    {item.status === 'error' && (
                      <span role="alert" className="text-destructive">
                        {getPreservedGraphMessage(item.error ?? '图谱更新失败')}
                      </span>
                    )}
                  </div>
                </div>
              ))}
              {failedBatchCount > 0 && (
                <div className="flex items-center justify-between gap-3 py-3 text-sm">
                  <span className="text-muted-foreground">模型或接口异常时可检查连接配置</span>
                  <button
                    type="button"
                    onClick={navigateToSettings}
                    className="font-medium text-primary hover:underline"
                  >
                    检查模型设置
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
        {/* 筛选栏 */}
        <FilterBar
          searchInput={searchInput}
          onSearchChange={handleSearchChange}
          categories={categories}
          selectedCategory={filters.category}
          onCategoryChange={handleCategoryChange}
          selectedTags={filters.tags}
          onTagsChange={handleTagsChange}
          activeFilterCount={activeFilterCount}
          onClearFilters={handleClearFilters}
        />

        {/* 结果统计 + 排序 */}
        <div className="mt-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <List className="h-4 w-4" />
            <span>
              关<span className="font-semibold text-foreground">{total}</span> 个题材
              {filters.q && <span>，搜索&quot;{filters.q}&quot;</span>}
              {filters.category && <span>，分类 {filters.category}</span>}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
              阶段
              <select
                aria-label="按生命周期阶段筛选"
                value={lifecycleFilter}
                onChange={(event) => setLifecycleFilter(event.target.value)}
                className="h-8 rounded-xl border border-border bg-background px-2 text-xs text-foreground"
              >
                <option value="">全部</option>
                <option value="germination">萌芽</option>
                <option value="fermentation">发酵</option>
                <option value="climax">高潮</option>
                <option value="divergence">分歧</option>
                <option value="ebb">退潮</option>
              </select>
            </label>
            <SortSelect
              sortBy={filters.sort_by}
              sortOrder={filters.sort_order}
              onSortChange={setSort}
            />
          </div>
        </div>

        {/* 主题列表 */}
        <section className="mt-4 space-y-3">
          {/* 加载状态*/}
          {isLoading && (
            <div className="space-y-3">
              {Array.from({ length: 10 }).map((_, i) => (
                <ThemeTableSkeleton key={i} />
              ))}
            </div>
          )}

          {/* 错误状态*/}
          {isError && (
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
          )}

          {/* 空状态*/}
          {!isLoading && !isError && themes.length === 0 && (
            <div className="flex flex-col items-center justify-center rounded-xl border border-border bg-card px-6 py-12">
              <Inbox className="h-10 w-10 text-muted-foreground" />
              <p className="mt-3 text-sm text-muted-foreground">
                {activeFilterCount > 0 ? '没有匹配当前筛选条件的题材' : '暂无题材数据'}
              </p>
              {activeFilterCount > 0 && (
                <button
                  onClick={clearFilters}
                  className="mt-3 text-sm text-primary hover:underline"
                >
                  清除筛选条件
                </button>
              )}
            </div>
          )}

          {/* 列表 */}
          {!isLoading && !isError && themes.length > 0 && (
            <>
              {themes.map((theme) => (
                <ThemeTableRow
                  key={theme.id}
                  theme={theme}
                  onClick={() => handleThemeClick(theme.id)}
                />
              ))}
            </>
          )}
        </section>

        {/* 分页 */}
        {!isLoading && !isError && totalPages > 1 && (
          <div className="mt-6">
            <Pagination page={filters.page} totalPages={totalPages} onPageChange={setPage} />
          </div>
        )}
      </main>
    </div>
  )
}
