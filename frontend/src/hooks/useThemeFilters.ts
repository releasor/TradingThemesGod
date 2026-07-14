/** URL 同步的题材筛选状态 Hook
 *
 * 将筛选参数同步到 URL search params，支持分享和书签。
 * 搜索输入使用 300ms 防抖。
 */

import { useState, useEffect, useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { ThemeListParams } from '@/types/theme'

const DEBOUNCE_MS = 300
const DEFAULT_PAGE_SIZE = 20

/** 从 URL params 解析筛选状态 */
function parseFilters(searchParams: URLSearchParams): ThemeListParams {
  return {
    page: Number(searchParams.get('page')) || 1,
    page_size: Number(searchParams.get('page_size')) || DEFAULT_PAGE_SIZE,
    sort_by: (searchParams.get('sort_by') as ThemeListParams['sort_by']) || 'heat_index',
    sort_order: (searchParams.get('sort_order') as ThemeListParams['sort_order']) || 'desc',
    category: searchParams.get('category') || undefined,
    tags: searchParams.get('tags') || undefined,
    q: searchParams.get('q') || undefined,
  }
}

export function useThemeFilters() {
  const [searchParams, setSearchParams] = useSearchParams()
  const filters = useMemo(() => parseFilters(searchParams), [searchParams])

  // 搜索输入的本地状态（防抖前）
  const [searchInput, setSearchInput] = useState(filters.q || '')

  // 防抖搜索：300ms 后更新 URL
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev)
        if (searchInput) {
          next.set('q', searchInput)
        } else {
          next.delete('q')
        }
        // 搜索时重置到第一页
        next.set('page', '1')
        return next
      }, { replace: true })
    }, DEBOUNCE_MS)

    return () => clearTimeout(timer)
  }, [searchInput, setSearchParams])

  // 更新筛选参数（非搜索）
  const updateFilter = useCallback(
    (key: string, value: string | undefined) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev)
        if (value) {
          next.set(key, value)
        } else {
          next.delete(key)
        }
        // 切换筛选时重置到第一页
        if (key !== 'page') {
          next.set('page', '1')
        }
        return next
      }, { replace: true })
    },
    [setSearchParams],
  )

  // 翻页
  const setPage = useCallback(
    (page: number) => {
      updateFilter('page', String(page))
    },
    [updateFilter],
  )

  // 排序变更
  const setSort = useCallback(
    (sortBy: ThemeListParams['sort_by'], sortOrder: ThemeListParams['sort_order']) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev)
        next.set('sort_by', sortBy)
        next.set('sort_order', sortOrder)
        next.set('page', '1')
        return next
      }, { replace: true })
    },
    [setSearchParams],
  )

  // 清除所有筛选
  const clearFilters = useCallback(() => {
    setSearchInput('')
    setSearchParams(new URLSearchParams(), { replace: true })
  }, [setSearchParams])

  // 活跃筛选计数
  const activeFilterCount = useMemo(
    () => [filters.q, filters.category, filters.tags].filter(Boolean).length,
    [filters.q, filters.category, filters.tags],
  )

  return {
    filters,
    searchInput,
    setSearchInput,
    updateFilter,
    setPage,
    setSort,
    clearFilters,
    activeFilterCount,
  }
}
