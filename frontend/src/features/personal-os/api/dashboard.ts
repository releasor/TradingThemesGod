import { apiClient } from '@/api/client'

export type DashboardSourceType =
  | 'chat_session'
  | 'note'
  | 'journal'
  | 'report'
  | 'decision'

export type OsDashboardPin = {
  id: number
  user_id: number
  source_type: DashboardSourceType
  source_id: number
  title: string
  snippet: string | null
  sort_order: number
  href: string
  created_at: string
  updated_at: string
}

export type OsOptimizeTip = {
  id: string
  title: string
  body: string
  priority: 'high' | 'medium' | 'low'
  action_href: string | null
  action_label: string | null
}

export type OsDashboardOverview = {
  display_name: string | null
  goals: string | null
  health_baseline: Record<string, unknown>
  module_flags: Record<string, boolean>
  has_report_tuning: boolean
  has_decision_tuning: boolean
  data_readiness: 'empty' | 'warmup' | 'ready'
  counts: {
    chat_sessions: number
    notes: number
    journal: number
    reports: number
    decisions: number
    pins: number
  }
  journal_by_kind: {
    diet: number
    training: number
    sleep: number
    schedule: number
  }
  recent: Array<{
    id: number
    source_type: DashboardSourceType
    title: string
    snippet: string | null
    href: string
    at: string | null
    pinned: boolean
  }>
  pins: OsDashboardPin[]
  optimize_tips: OsOptimizeTip[]
}

export async function fetchOsDashboard(): Promise<OsDashboardOverview> {
  const { data } = await apiClient.get<OsDashboardOverview>('/os/dashboard')
  return data
}

export async function listOsDashboardPins(): Promise<OsDashboardPin[]> {
  const { data } = await apiClient.get<OsDashboardPin[]>('/os/dashboard/pins')
  return data
}

export async function pinToOsDashboard(input: {
  source_type: DashboardSourceType
  source_id: number
  title?: string
  snippet?: string
}): Promise<OsDashboardPin> {
  const { data } = await apiClient.post<OsDashboardPin>('/os/dashboard/pins', input)
  return data
}

export async function unpinFromOsDashboard(pinId: number): Promise<void> {
  await apiClient.delete(`/os/dashboard/pins/${pinId}`)
}

export async function unpinOsDashboardBySource(
  sourceType: DashboardSourceType,
  sourceId: number
): Promise<void> {
  await apiClient.delete(`/os/dashboard/pins/by-source/${sourceType}/${sourceId}`)
}
