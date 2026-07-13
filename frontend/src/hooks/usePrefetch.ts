/** 数据预取 Hook

在用户 hover 时预取详情数据，提升页面切换速度。
*/

import { useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { fetchThemeDetail, fetchStockDetail } from '@/api/theme'

/**
 * 题材详情预取 Hook
 *
 * @example
 * ```tsx
 * const prefetchTheme = usePrefetchTheme()
 *
 * <Link
 *   to={`/themes/${theme.id}`}
 *   onMouseEnter={() => prefetchTheme(theme.id)}
 * >
 *   {theme.name}
 * </Link>
 * ```
 */
export function usePrefetchTheme() {
  const queryClient = useQueryClient()

  return useCallback(
    (themeId: number) => {
      queryClient.prefetchQuery({
        queryKey: ['theme-detail', themeId],
        queryFn: () => fetchThemeDetail(themeId),
        staleTime: 5 * 60 * 1000, // 5 分钟
      })
    },
    [queryClient]
  )
}

/**
 * 股票详情预取 Hook
 *
 * @example
 * ```tsx
 * const prefetchStock = usePrefetchStock()
 *
 * <button
 *   onMouseEnter={() => prefetchStock(stock.code)}
 *   onClick={() => showStockDetail(stock.code)}
 * >
 *   {stock.name}
 * </button>
 * ```
 */
export function usePrefetchStock() {
  const queryClient = useQueryClient()

  return useCallback(
    (stockCode: string) => {
      queryClient.prefetchQuery({
        queryKey: ['stock-detail', stockCode],
        queryFn: () => fetchStockDetail(stockCode),
        staleTime: 5 * 60 * 1000, // 5 分钟
      })
    },
    [queryClient]
  )
}
