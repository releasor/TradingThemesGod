/** 系统统计 API */

import { apiClient } from '@/api/client'

export interface SystemStats {
  themes: { total: number; categories: Array<{ category: string; count: number }> }
  stocks: { total: number }
  events: { total: number }
  chains: { total: number }
  scraper: {
    last_run: {
      id: number
      source: string
      status: string
      created_at: string
    } | null
  }
}

export async function fetchSystemStats(): Promise<SystemStats> {
  const { data } = await apiClient.get<SystemStats>('/stats')
  return data
}
