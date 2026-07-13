/** 题材 API 客户端
 *
 * 封装 /api/v1/themes 相关请求。
 */

import axios from 'axios'
import type { ThemeRankingResponse } from '@/types/theme'

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 10_000,
})

/** 获取题材排名（按热度降序） */
export async function fetchThemeRanking(limit = 20): Promise<ThemeRankingResponse> {
  const { data } = await apiClient.get<ThemeRankingResponse>('/themes/ranking', {
    params: { limit },
  })
  return data
}
