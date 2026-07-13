/** 股票 API 客户端
 *
 * 封装 /api/v1/stocks 相关请求。
 */

import { apiClient } from '@/api/client'
import type { StockDetailResponse } from '@/types/stock'

/** 获取股票详情（含最近事件） */
export async function fetchStockDetail(code: string): Promise<StockDetailResponse> {
  const { data } = await apiClient.get<StockDetailResponse>(`/stocks/${code}`)
  return data
}
