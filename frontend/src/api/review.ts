/** 复盘台 API */

import { apiClient } from '@/api/client'
import type {
  ReviewAiReportResponse,
  ReviewDayListResponse,
  ReviewDayResponse,
  ReviewThemeResponse,
} from '@/types/review'

export async function fetchReviewDays(
  params: { from?: string; to?: string } = {}
): Promise<ReviewDayListResponse> {
  const { data } = await apiClient.get<ReviewDayListResponse>('/review/days', {
    params: {
      ...(params.from ? { from: params.from } : {}),
      ...(params.to ? { to: params.to } : {}),
    },
  })
  return data
}

export async function fetchReviewDay(date: string): Promise<ReviewDayResponse> {
  const { data } = await apiClient.get<ReviewDayResponse>(`/review/days/${date}`)
  return data
}

export async function fetchReviewTheme(
  themeId: number,
  days = 10
): Promise<ReviewThemeResponse> {
  const { data } = await apiClient.get<ReviewThemeResponse>(`/review/themes/${themeId}`, {
    params: { days },
  })
  return data
}

export async function fetchReviewReport(
  date: string
): Promise<ReviewAiReportResponse | null> {
  const { data } = await apiClient.get<ReviewAiReportResponse | null>(
    `/review/days/${date}/report`
  )
  return data ?? null
}

export async function ensureReviewReport(date: string): Promise<ReviewAiReportResponse> {
  const { data } = await apiClient.post<ReviewAiReportResponse>(
    `/review/days/${date}/report/ensure`,
    null,
    { timeout: 60_000 }
  )
  return data
}
