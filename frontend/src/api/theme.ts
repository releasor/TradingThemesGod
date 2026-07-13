/** 题材 API 客户端
 *
 * 封装 /api/v1/themes 相关请求。
 */

import { apiClient } from '@/api/client'
import type {
  ThemeRankingResponse,
  ThemeListParams,
  ThemeListResponse,
  ThemeCategoriesResponse,
  ThemeDetailResponse,
} from '@/types/theme'
import type { StockListResponse } from '@/types/stock'

/** 获取题材排名（按热度降序） */
export async function fetchThemeRanking(limit = 20): Promise<ThemeRankingResponse> {
  const { data } = await apiClient.get<ThemeRankingResponse>('/themes/ranking', {
    params: { limit },
  })
  return data
}

/** 获取题材列表（支持分页、排序、筛选） */
export async function fetchThemes(
  params: ThemeListParams,
  signal?: AbortSignal
): Promise<ThemeListResponse> {
  // 当有搜索关键词时使用 search 端点，否则使用 list 端点
  if (params.q) {
    const { data } = await apiClient.get<ThemeListResponse>('/themes/search', {
      params: {
        q: params.q,
        page: params.page,
        page_size: params.page_size,
      },
      signal,
    })
    return data
  }

  const { data } = await apiClient.get<ThemeListResponse>('/themes', {
    params: {
      page: params.page,
      page_size: params.page_size,
      sort_by: params.sort_by,
      sort_order: params.sort_order,
      category: params.category || undefined,
      tags: params.tags || undefined,
    },
    signal,
  })
  return data
}

/** 获取所有题材分类 */
export async function fetchCategories(): Promise<ThemeCategoriesResponse> {
  const { data } = await apiClient.get<ThemeCategoriesResponse>('/themes/categories')
  return data
}

/** 获取题材详情（含产业链数据） */
export async function fetchThemeDetail(id: number): Promise<ThemeDetailResponse> {
  const { data } = await apiClient.get<ThemeDetailResponse>(`/themes/${id}`)
  return data
}

/** 获取题材关联的股票列表 */
export async function fetchThemeStocks(
  themeId: number,
  chainLevel?: string,
  page = 1,
  pageSize = 100
): Promise<StockListResponse> {
  const { data } = await apiClient.get<StockListResponse>(`/themes/${themeId}/stocks`, {
    params: {
      chain_level: chainLevel || undefined,
      page,
      page_size: pageSize,
    },
  })
  return data
}
