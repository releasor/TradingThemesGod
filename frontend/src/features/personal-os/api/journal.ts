import { apiClient } from '@/api/client'

export type JournalKind = 'diet' | 'training' | 'sleep' | 'schedule'

export type OsJournalEntry = {
  id: number
  user_id: number
  kind: JournalKind
  occurred_at: string
  payload: Record<string, unknown>
  note: string | null
  media_refs: string[]
  created_at: string
  updated_at: string
}

export async function listOsJournal(params?: {
  kind?: JournalKind
  day?: string
  limit?: number
}): Promise<OsJournalEntry[]> {
  const { data } = await apiClient.get<OsJournalEntry[]>('/os/journal', { params })
  return data
}

export async function createOsJournal(input: {
  kind: JournalKind
  occurred_at: string
  payload?: Record<string, unknown>
  note?: string
}): Promise<OsJournalEntry> {
  const { data } = await apiClient.post<OsJournalEntry>('/os/journal', input)
  return data
}

export async function deleteOsJournal(id: number): Promise<void> {
  await apiClient.delete(`/os/journal/${id}`)
}
