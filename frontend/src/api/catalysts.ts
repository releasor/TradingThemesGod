/** 催化雷达 API */

import { apiClient } from '@/api/client'
import type {
  CatalystEnsureParams,
  CatalystEnsureResponse,
  CatalystFeedParams,
  CatalystFeedResponse,
  CatalystThemeSummaryResponse,
} from '@/types/catalyst'

export async function fetchCatalystFeed(
  params: CatalystFeedParams = {}
): Promise<CatalystFeedResponse> {
  const { data } = await apiClient.get<CatalystFeedResponse>('/catalysts/feed', {
    params: {
      ...(params.freshness ? { freshness: params.freshness } : {}),
      ...(params.actor_type ? { actor_type: params.actor_type } : {}),
      ...(params.theme_id != null ? { theme_id: params.theme_id } : {}),
      ...(params.q ? { q: params.q } : {}),
      ...(params.from ? { from: params.from } : {}),
      ...(params.to ? { to: params.to } : {}),
      ...(params.limit != null ? { limit: params.limit } : {}),
      ...(params.offset != null ? { offset: params.offset } : {}),
    },
  })
  return data
}

export async function fetchCatalystThemeSummary(
  themeId: number
): Promise<CatalystThemeSummaryResponse> {
  const { data } = await apiClient.get<CatalystThemeSummaryResponse>(
    `/catalysts/themes/${themeId}/summary`
  )
  return data
}

export async function ensureCatalystClassify(
  params: CatalystEnsureParams = {}
): Promise<CatalystEnsureResponse> {
  const { data } = await apiClient.post<CatalystEnsureResponse>(
    '/catalysts/classify/ensure',
    null,
    {
      params: {
        days: params.days ?? 7,
        use_model: params.use_model ?? false,
      },
      timeout: 60_000,
    }
  )
  return data
}
