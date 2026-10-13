import { apiClient } from '@/api/client'

export type OsNote = {
  id: number
  user_id: number
  title: string
  body: string
  tags: string[]
  created_at: string
  updated_at: string
}

export async function listOsNotes(q?: string): Promise<OsNote[]> {
  const { data } = await apiClient.get<OsNote[]>('/os/notes', {
    params: q ? { q } : undefined,
  })
  return data
}

export async function createOsNote(input: {
  title: string
  body: string
  tags?: string[]
}): Promise<OsNote> {
  const { data } = await apiClient.post<OsNote>('/os/notes', input)
  return data
}

export async function updateOsNote(
  id: number,
  input: { title?: string; body?: string; tags?: string[] }
): Promise<OsNote> {
  const { data } = await apiClient.patch<OsNote>(`/os/notes/${id}`, input)
  return data
}

export async function deleteOsNote(id: number): Promise<void> {
  await apiClient.delete(`/os/notes/${id}`)
}
