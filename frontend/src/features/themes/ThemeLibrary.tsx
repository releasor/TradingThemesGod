/** 题材库主页面
 *
 * 浏览所有题材，支持搜索、筛选、排序和分页。
 * 筛选状态同步到 URL search params，支持分享。
 */

import { useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { RefreshCw, AlertCircle, Inbox, List } from 'lucide-react'
import { fetchThemes, fetchCategories } from '@/api/theme'
import { useThemeFilters } from '@/hooks/useThemeFilters'
import { FilterBar } from '@/components/FilterBar'
import { SortSelect } from '@/components/SortSelect'
import { ExportButton } from '@/components/ExportButton'
import { ThemeTableRow } from '@/components/ThemeTableRow'
import { ThemeTableSkeleton } from '@/components/ThemeTableSkeleton'
import { Pagination } from '@/components/Pagination'

export function ThemeLibrary() {
  const navigate = useNavigate()
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
    (themeId: number) => navigate(`/themes/${themeId}`),
    [navigate],
  )

  // 获取题材列表
  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['themes', filters],
    queryFn: ({ signal }) => fetchThemes(filters, signal),
  })

  // 获取分类列表（缓存较长时间）
  const { data: categoriesData } = useQuery({
    queryKey: ['theme-categories'],
    queryFn: fetchCategories,
    staleTime: 10 * 60 * 1000, // 10 分钟
  })

  const themes = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = data?.total_pages ?? 0
  const categories = categoriesData?.categories ?? []

  return (
    <div className="min-h-screen bg-background">
      {/* 页头 */}
      <header className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-foreground">
              TradingThemesGod
            </h1>
            <span className="text-muted-foreground font-normal">题材库</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/')}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              看板
            </button>
            <ExportButton data={themes} />
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="inline-flex items-center gap-2 rounded-md border border-border bg-card px-3 py-2 text-sm font-medium text-card-foreground transition-colors hover:bg-accent disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
              刷新
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        {/* 筛选栏 */}
        <FilterBar
          searchInput={searchInput}
          onSearchChange={setSearchInput}
          categories={categories}
          selectedCategory={filters.category}
          onCategoryChange={(v) => updateFilter('category', v)}
          selectedTags={filters.tags}
          onTagsChange={(v) => updateFilter('tags', v)}
          activeFilterCount={activeFilterCount}
          onClearFilters={clearFilters}
        />

        {/* 结果统计 + 排序 */}
        <div className="mt-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <List className="h-4 w-4" />
            <span>
              共 <span className="font-semibold text-foreground">{total}</span> 个题材
              {filters.q && (
                <span>
                  ，搜索 &quot;{filters.q}&quot;
                </span>
              )}
              {filters.category && (
                <span>
                  ，分类: {filters.category}
                </span>
              )}
            </span>
          </div>
          <SortSelect
            sortBy={filters.sort_by}
            sortOrder={filters.sort_order}
            onSortChange={setSort}
          />
        </div>

        {/* 主题列表 */}
        <section className="mt-4 space-y-3">
          {/* 加载状态 */}
          {isLoading && (
            <div className="space-y-3">
              {Array.from({ length: 10 }).map((_, i) => (
                <ThemeTableSkeleton key={i} />
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
                {activeFilterCount > 0
                  ? '没有匹配当前筛选条件的题材'
                  : '暂无题材数据'}
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
            <Pagination
              page={filters.page}
              totalPages={totalPages}
              onPageChange={setPage}
            />
          </div>
        )}
      </main>
    </div>
  )
}
