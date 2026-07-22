import { apiClient } from '@/api/client'

export interface NewsArticle {
  id: number
  source: string
  category: string
  title: string
  summary: string | null
  url: string
  published_at: string
  crawled_at: string
  heat_score: number
}

export interface NewsListResponse {
  items: NewsArticle[]
  total: number
}

export interface NewsSourceResult {
  source: string
  success: boolean
  fetched_count: number
  error: string | null
}

export interface NewsRefreshResponse {
  success: boolean
  fetched_count: number
  inserted_count: number
  refreshed_at: string
  sources: NewsSourceResult[]
}

export async function fetchNews(
  limit = 50,
  sources?: string[],
  offset = 0
): Promise<NewsListResponse> {
  const { data } = await apiClient.get<NewsListResponse>('/news', {
    params: { limit, offset, ...(sources ? { sources: sources.join(',') } : {}) },
  })
  return data
}

export async function fetchNewsSources(): Promise<string[]> {
  const { data } = await apiClient.get<string[]>('/news/sources')
  return data
}

export async function refreshNews(sources?: string[]): Promise<NewsRefreshResponse> {
  const { data } = await apiClient.post<NewsRefreshResponse>('/news/refresh', { sources })
  return data
}
