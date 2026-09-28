import { apiClient } from '@/api/client'

export interface PromptItem {
  id: number
  user_id: number
  title: string
  body: string
  category: string | null
  tags: string[]
  enabled: boolean
  pinned: boolean
  sort_order: number
  created_at: string
  updated_at: string
}

export interface PromptItemInput {
  title: string
  body: string
  category?: string | null
  tags?: string[]
  enabled?: boolean
  pinned?: boolean
  sort_order?: number
}

export async function listPromptItems(params?: {
  q?: string
  category?: string
  tag?: string
  enabled?: boolean
}): Promise<PromptItem[]> {
  const { data } = await apiClient.get<PromptItem[]>('/prompt/items', { params })
  return data
}

export async function createPromptItem(input: PromptItemInput): Promise<PromptItem> {
  const { data } = await apiClient.post<PromptItem>('/prompt/items', input)
  return data
}

export async function updatePromptItem(
  id: number,
  input: Partial<PromptItemInput>
): Promise<PromptItem> {
  const { data } = await apiClient.put<PromptItem>(`/prompt/items/${id}`, input)
  return data
}

export async function deletePromptItem(id: number): Promise<void> {
  await apiClient.delete(`/prompt/items/${id}`)
}
