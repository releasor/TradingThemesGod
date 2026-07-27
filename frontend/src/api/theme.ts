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
  ConceptGraphRefreshResponse,
  ConceptGraphBatchItem,
  ThemeInsightRefreshResponse,
} from '@/types/theme'
import type { StockListResponse } from '@/types/stock'

/** 获取题材排名（按热度降序） */
export async function fetchThemeRanking(
  limit = 20,
  signal?: AbortSignal
): Promise<ThemeRankingResponse> {
  const { data } = await apiClient.get<ThemeRankingResponse>('/themes/ranking', {
    params: { limit },
    signal,
  })
  return data
}

/** 获取独立展示的市场表现板块。 */
export async function fetchMarketSignals(signal?: AbortSignal): Promise<ThemeRankingResponse> {
  const { data } = await apiClient.get<ThemeRankingResponse>('/themes/market-signals', { signal })
  return {
    ...data,
    items: data.items.map((item) => ({
      ...item,
      heat_index: Number(item.heat_index),
      rise_fall_pct: Number(item.rise_fall_pct),
    })),
  }
}

/** 获取独立展示的行情指标板块（新高、财报预告、破增发等）。 */
export async function fetchIndicatorSignals(signal?: AbortSignal): Promise<ThemeRankingResponse> {
  const { data } = await apiClient.get<ThemeRankingResponse>('/themes/indicator-signals', {
    signal,
  })
  return {
    ...data,
    items: data.items.map((item) => ({
      ...item,
      heat_index: Number(item.heat_index),
      rise_fall_pct: Number(item.rise_fall_pct),
    })),
  }
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

/** 抓取真实公开资料并增量刷新单个题材图谱。 */
export async function refreshConceptGraph(id: number): Promise<ConceptGraphRefreshResponse> {
  const { data } = await apiClient.post<ConceptGraphRefreshResponse>(
    `/themes/${id}/concept-graph/refresh`,
    undefined,
    { timeout: 300_000 }
  )
  return data
}

export async function refreshThemeInsights(id: number): Promise<ThemeInsightRefreshResponse> {
  const { data } = await apiClient.post<ThemeInsightRefreshResponse>(
    `/themes/${id}/insights/refresh`,
    undefined,
    { timeout: 300_000 }
  )
  return data
}

/** 有限批量刷新题材图谱。 */
export async function refreshConceptGraphs(
  themeIds: number[],
  limit = 5
): Promise<ConceptGraphBatchItem[]> {
  const { data } = await apiClient.post<{ items: ConceptGraphBatchItem[] }>(
    '/themes/concept-graphs/refresh',
    { theme_ids: themeIds, limit },
    { timeout: 900_000 }
  )
  return data.items
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
