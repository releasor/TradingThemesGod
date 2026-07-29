import { apiClient } from './client'

export interface TushareSettings {
  enabled: boolean
  has_token: boolean
  updated_at: string | null
}

export interface TushareSettingsUpdate {
  enabled: boolean
  token?: string | null
}

export interface TushareTestResult {
  success: boolean
  message: string
}

export async function fetchTushareSettings(): Promise<TushareSettings> {
  const { data } = await apiClient.get<TushareSettings>('/integrations/tushare')
  return data
}

export async function updateTushareSettings(
  payload: TushareSettingsUpdate
): Promise<TushareSettings> {
  const { data } = await apiClient.put<TushareSettings>('/integrations/tushare', payload)
  return data
}

export async function testTushareConnection(token?: string): Promise<TushareTestResult> {
  const { data } = await apiClient.post<TushareTestResult>('/integrations/tushare/test', {
    token: token || null,
  })
  return data
}
