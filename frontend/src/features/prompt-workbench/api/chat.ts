import { apiClient } from '@/api/client'

export interface ChatSession {
  id: number
  user_id: number
  title: string
  provider_id: number | null
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  id: number
  session_id: number
  role: string
  content: string
  created_at: string
}

export async function listChatSessions(): Promise<ChatSession[]> {
  const { data } = await apiClient.get<ChatSession[]>('/prompt/chat/sessions')
  return data
}

export async function createChatSession(input?: {
  title?: string
  provider_id?: number | null
}): Promise<ChatSession> {
  const { data } = await apiClient.post<ChatSession>('/prompt/chat/sessions', input ?? {})
  return data
}

export async function updateChatSession(
  id: number,
  input: { title?: string; provider_id?: number | null }
): Promise<ChatSession> {
  const { data } = await apiClient.patch<ChatSession>(`/prompt/chat/sessions/${id}`, input)
  return data
}

export async function deleteChatSession(id: number): Promise<void> {
  await apiClient.delete(`/prompt/chat/sessions/${id}`)
}

export async function listChatMessages(sessionId: number): Promise<ChatMessage[]> {
  const { data } = await apiClient.get<ChatMessage[]>(
    `/prompt/chat/sessions/${sessionId}/messages`
  )
  return data
}

export async function sendChatMessage(
  sessionId: number,
  input: { content: string; provider_id?: number | null }
): Promise<ChatMessage> {
  const { data } = await apiClient.post<ChatMessage>(
    `/prompt/chat/sessions/${sessionId}/messages`,
    input,
    { timeout: 180_000 }
  )
  return data
}
