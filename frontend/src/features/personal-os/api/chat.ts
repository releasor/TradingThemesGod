import { apiClient } from '@/api/client'
import { getAuthToken } from '@/stores/auth'

export const OS_LLM_TIMEOUT_MS = 180_000

export type OsChatSession = {
  id: number
  user_id: number
  title: string
  provider_id: number | null
  created_at: string
  updated_at: string
}

export type OsChatMessage = {
  id: number
  session_id: number
  role: string
  content: string
  provider_id?: number | null
  created_at: string
}

export type OsStreamEvent =
  | { type: 'start' }
  | { type: 'status'; message: string }
  | { type: 'delta'; text: string }
  | { type: 'done'; result: string; message_id?: number; run_id?: number | null }
  | { type: 'error'; message: string }

export class OsStreamAbortError extends Error {
  readonly reason: 'timeout' | 'cancel'
  constructor(reason: 'timeout' | 'cancel') {
    super(reason === 'timeout' ? '等待模型响应超时，请重试或更换模型' : '已停止生成')
    this.name = 'OsStreamAbortError'
    this.reason = reason
  }
}

export async function listOsChatSessions(): Promise<OsChatSession[]> {
  const { data } = await apiClient.get<OsChatSession[]>('/os/chat/sessions')
  return data
}

export async function createOsChatSession(input?: {
  title?: string
  provider_id?: number | null
}): Promise<OsChatSession> {
  const { data } = await apiClient.post<OsChatSession>('/os/chat/sessions', input ?? {})
  return data
}

export async function updateOsChatSession(
  id: number,
  input: { title?: string; provider_id?: number | null }
): Promise<OsChatSession> {
  const { data } = await apiClient.patch<OsChatSession>(`/os/chat/sessions/${id}`, input)
  return data
}

export async function deleteOsChatSession(id: number): Promise<void> {
  await apiClient.delete(`/os/chat/sessions/${id}`)
}

export async function listOsChatMessages(sessionId: number): Promise<OsChatMessage[]> {
  const { data } = await apiClient.get<OsChatMessage[]>(
    `/os/chat/sessions/${sessionId}/messages`
  )
  return data
}

/** 非流式发送（流式失败时的回退） */
export async function sendOsChatMessage(
  sessionId: number,
  input: { content: string; provider_id?: number | null }
): Promise<OsChatMessage> {
  const { data } = await apiClient.post<OsChatMessage>(
    `/os/chat/sessions/${sessionId}/messages`,
    input,
    { timeout: OS_LLM_TIMEOUT_MS }
  )
  return data
}

export async function sendOsChatMessageStream(
  sessionId: number,
  input: { content: string; provider_id?: number | null },
  onEvent: (event: OsStreamEvent) => void,
  signal?: AbortSignal
): Promise<{ result: string; message_id?: number }> {
  const controller = new AbortController()
  let timedOut = false
  const onAbort = () => controller.abort()
  signal?.addEventListener('abort', onAbort)
  const timer = window.setTimeout(() => {
    timedOut = true
    controller.abort()
  }, OS_LLM_TIMEOUT_MS)

  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    }
    const token = getAuthToken()
    if (token) headers.Authorization = `Bearer ${token}`

    const response = await fetch(`/api/v1/os/chat/sessions/${sessionId}/messages/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify(input),
      signal: controller.signal,
    })
    if (!response.ok) {
      let detail = `请求失败（${response.status}）`
      try {
        const data = (await response.json()) as { detail?: string }
        if (data.detail) detail = data.detail
      } catch {
        /* ignore */
      }
      throw new Error(detail)
    }
    if (!response.body) throw new Error('响应体为空')

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let finalResult = ''
    let messageId: number | undefined
    let sawDone = false

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const chunks = buffer.split('\n\n')
      buffer = chunks.pop() ?? ''
      for (const chunk of chunks) {
        const dataLines = chunk
          .split('\n')
          .filter((line) => line.startsWith('data:'))
          .map((line) => line.slice(5).trimStart())
        if (dataLines.length === 0) continue
        const raw = dataLines.join('\n')
        if (raw === '[DONE]') continue
        let event: OsStreamEvent
        try {
          event = JSON.parse(raw) as OsStreamEvent
        } catch {
          continue
        }
        onEvent(event)
        if (event.type === 'delta') finalResult += event.text
        else if (event.type === 'done') {
          finalResult = event.result
          messageId = event.message_id
          sawDone = true
        } else if (event.type === 'error') {
          throw new Error(event.message)
        }
      }
    }
    if (!sawDone) throw new Error('流式响应异常中断，未收到完成事件')
    return { result: finalResult, message_id: messageId }
  } catch (err) {
    if ((err as Error).name === 'AbortError') {
      throw new OsStreamAbortError(timedOut ? 'timeout' : 'cancel')
    }
    throw err
  } finally {
    window.clearTimeout(timer)
    signal?.removeEventListener('abort', onAbort)
  }
}
