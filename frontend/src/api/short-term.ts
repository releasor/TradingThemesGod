import { apiClient } from '@/api/client'
import type {
  FirstToSecondCandidateResponse,
  ShortTermOverviewResponse,
  ShortTermPeriod,
} from '@/types/short-term'

interface FetchShortTermOverviewParams {
  tradeDate?: string
  period?: ShortTermPeriod
  startDate?: string
  endDate?: string
}

export async function fetchShortTermOverview({
  tradeDate,
  period = 'today',
  startDate,
  endDate,
}: FetchShortTermOverviewParams = {}): Promise<ShortTermOverviewResponse> {
  const { data } = await apiClient.get<ShortTermOverviewResponse>('/short-term/overview', {
    params: {
      ...(tradeDate ? { trade_date: tradeDate } : {}),
      period,
      ...(startDate ? { start_date: startDate } : {}),
      ...(endDate ? { end_date: endDate } : {}),
    },
    timeout: 300_000,
  })
  return data
}

interface FirstToSecondParams {
  tradeDate?: string
}

export async function fetchFirstToSecondCandidates({
  tradeDate,
}: FirstToSecondParams = {}): Promise<FirstToSecondCandidateResponse> {
  const { data } = await apiClient.get<FirstToSecondCandidateResponse>(
    '/short-term/first-to-second',
    {
      params: {
        ...(tradeDate ? { trade_date: tradeDate } : {}),
      },
      timeout: 300_000,
    }
  )
  return data
}

export async function refreshFirstToSecondCandidates({
  tradeDate,
}: FirstToSecondParams = {}): Promise<FirstToSecondCandidateResponse> {
  const { data } = await apiClient.post<FirstToSecondCandidateResponse>(
    '/short-term/first-to-second/refresh',
    null,
    {
      params: {
        ...(tradeDate ? { trade_date: tradeDate } : {}),
      },
      timeout: 300_000,
    }
  )
  return data
}
