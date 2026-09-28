import { apiClient } from '@/api/client'
import { getAuthToken } from '@/stores/auth'

const LLM_TIMEOUT_MS = 180_000

export interface TextResult {
  result: string
  run_id: number | null
}

export interface DualTestResult {
  output_a: string
  output_b: string
}

export type StreamEvent =
  | { type: 'start' }
  | { type: 'status'; message: string }
  | { type: 'delta'; text: string }
  | { type: 'done'; result: string; run_id: number | null }
  | { type: 'error'; message: string }

async function readSseStream(
  response: Response,
  onEvent: (event: StreamEvent) => void
): Promise<TextResult> {
  if (!response.ok) {
    let message = `请求失败 (${response.status})`
    try {
      const data = (await response.json()) as { detail?: string; message?: string }
      message = data.detail || data.message || message
    } catch {
      /* ignore */
    }
    throw new Error(message)
  }
  if (!response.body) {
    throw new Error('浏览器不支持流式响应')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finalResult = ''
  let runId: number | null = null
  let sawDone = false

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const chunks = buffer.split('\n\n')
    buffer = chunks.pop() ?? ''
    for (const chunk of chunks) {
      const line = chunk
        .split('\n')
        .map((l) => l.trim())
        .find((l) => l.startsWith('data:'))
      if (!line) continue
      const raw = line.slice(5).trim()
      if (!raw) continue
      let event: StreamEvent
      try {
        event = JSON.parse(raw) as StreamEvent
      } catch {
        continue
      }
      onEvent(event)
      if (event.type === 'delta') {
        finalResult += event.text
      } else if (event.type === 'done') {
        finalResult = event.result
        runId = event.run_id
        sawDone = true
      } else if (event.type === 'error') {
        throw new Error(event.message)
      }
    }
  }

  if (!sawDone) {
    throw new Error('流式响应异常中断，未收到完成事件')
  }

  return { result: finalResult, run_id: runId }
}

function authHeaders(): HeadersInit {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'text/event-stream',
  }
  const token = getAuthToken()
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}

async function fetchStream(
  path: string,
  body: unknown,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal
): Promise<TextResult> {
  const controller = new AbortController()
  const onAbort = () => controller.abort()
  signal?.addEventListener('abort', onAbort)
  const timer = window.setTimeout(() => controller.abort(), LLM_TIMEOUT_MS)
  try {
    const response = await fetch(`/api/v1${path}`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(body),
      signal: controller.signal,
    })
    return await readSseStream(response, onEvent)
  } finally {
    window.clearTimeout(timer)
    signal?.removeEventListener('abort', onAbort)
  }
}

export async function designPrompt(input: {
  goal: string
  notes?: string
  provider_id?: number | null
}): Promise<TextResult> {
  const { data } = await apiClient.post<TextResult>('/prompt/design', input, {
    timeout: LLM_TIMEOUT_MS,
  })
  return data
}

export async function optimizePrompt(input: {
  source: string
  mode: 'smart' | 'framework'
  framework?: string | null
  extra_goal?: string | null
  provider_id?: number | null
  persist?: boolean
}): Promise<TextResult> {
  const { data } = await apiClient.post<TextResult>('/prompt/optimize', input, {
    timeout: LLM_TIMEOUT_MS,
  })
  return data
}

export async function optimizePromptStream(
  input: {
    source: string
    mode: 'smart' | 'framework'
    framework?: string | null
    extra_goal?: string | null
    provider_id?: number | null
    persist?: boolean
  },
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal
): Promise<TextResult> {
  const response = await fetchStream(
    '/prompt/optimize/stream',
    input,
    onEvent,
    signal
  )
  return response
}

export async function iteratePrompt(input: {
  run_id?: number | null
  current: string
  instruction: string
  provider_id?: number | null
}): Promise<TextResult> {
  const { data } = await apiClient.post<TextResult>('/prompt/optimize/iterate', input, {
    timeout: LLM_TIMEOUT_MS,
  })
  return data
}

export async function iteratePromptStream(
  input: {
    run_id?: number | null
    current: string
    instruction: string
    provider_id?: number | null
  },
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal
): Promise<TextResult> {
  return fetchStream('/prompt/optimize/iterate/stream', input, onEvent, signal)
}

export async function dualTestPrompts(input: {
  prompt_a: string
  prompt_b: string
  user_message: string
  provider_id?: number | null
}): Promise<DualTestResult> {
  const { data } = await apiClient.post<DualTestResult>('/prompt/test', input, {
    timeout: LLM_TIMEOUT_MS,
  })
  return data
}
