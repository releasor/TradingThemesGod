import { apiClient } from '@/api/client'
import type {
  FirstToSecondCandidateResponse,
  SectorRotationResponse,
  ShortTermOverviewResponse,
  ShortTermPeriod,
  ShortTermSignalRefreshResponse,
  ThemeLifecycleResponse,
} from '@/types/short-term'

interface FetchShortTermOverviewParams {
  tradeDate?: string
  period?: ShortTermPeriod
  startDate?: string
  endDate?: string
}

function buildShortTermOverviewParams({
  tradeDate,
  period = 'today',
  startDate,
  endDate,
}: FetchShortTermOverviewParams = {}) {
  return {
    ...(tradeDate ? { trade_date: tradeDate } : {}),
    period,
    ...(startDate ? { start_date: startDate } : {}),
    ...(endDate ? { end_date: endDate } : {}),
  }
}

export async function fetchShortTermOverview(
  params: FetchShortTermOverviewParams = {}
): Promise<ShortTermOverviewResponse> {
  const { data } = await apiClient.get<ShortTermOverviewResponse>('/short-term/overview', {
    params: buildShortTermOverviewParams(params),
    timeout: 30_000,
  })
  return data
}

export async function refreshShortTermData(
  params: FetchShortTermOverviewParams = {}
): Promise<ShortTermOverviewResponse> {
  const { data } = await apiClient.post<ShortTermOverviewResponse>(
    '/short-term/overview/refresh-data',
    null,
    {
      params: buildShortTermOverviewParams(params),
      timeout: 300_000,
    }
  )
  return data
}

export async function analyzeShortTermFromDatabase(
  params: FetchShortTermOverviewParams = {},
  options: { timeout?: number } = {}
): Promise<ShortTermOverviewResponse> {
  const { data } = await apiClient.post<ShortTermOverviewResponse>(
    '/short-term/overview/analyze',
    null,
    {
      params: buildShortTermOverviewParams(params),
      timeout: options.timeout ?? 300_000,
    }
  )
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

export async function refreshShortTermSignals(tradeDate?: string) {
  const { data } = await apiClient.post<ShortTermSignalRefreshResponse>(
    '/short-term/signals/refresh',
    null,
    {
      params: tradeDate ? { trade_date: tradeDate } : {},
      timeout: 300_000,
    }
  )
  return data
}

export async function fetchShortTermSectors(tradeDate?: string) {
  const { data } = await apiClient.get<SectorRotationResponse>('/short-term/sectors', {
    params: tradeDate ? { trade_date: tradeDate } : {},
    timeout: 30_000,
  })
  return data
}

export async function fetchThemeLifecycle(themeId: number, days = 10) {
  const { data } = await apiClient.get<ThemeLifecycleResponse>(
    `/short-term/themes/${themeId}/lifecycle`,
    {
      params: { days },
      timeout: 30_000,
    }
  )
  return data
}
