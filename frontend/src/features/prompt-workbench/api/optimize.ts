import { apiClient } from '@/api/client'
import { getAuthToken } from '@/stores/auth'

/** LLM 调用超时（毫秒）— 与后端流式代理一致 */
export const LLM_TIMEOUT_MS = 180_000

export type StreamEvent =
  | { type: 'start' }
  | { type: 'status'; message: string }
  | { type: 'delta'; text: string }
  | { type: 'done'; result: string; run_id: number | null }
  | { type: 'persisted'; run_id: number }
  | { type: 'error'; message: string }

export type TextResult = {
  result: string
  run_id: number | null
}

export type DualTestResult = {
  output_a: string
  output_b: string
}

export type OptimizeRunSummary = {
  id: number
  source: string
  result: string
  mode: string
  framework: string | null
  extra_goal: string | null
  version_count: number
  created_at: string
  updated_at: string
}

export type OptimizeRunDetail = {
  id: number
  source: string
  result: string
  mode: string
  framework: string | null
  extra_goal: string | null
  versions: Array<{ result?: string; instruction?: string } | string>
  created_at: string
  updated_at: string
}

export class StreamAbortError extends Error {
  readonly reason: 'timeout' | 'cancel'

  constructor(reason: 'timeout' | 'cancel') {
    super(reason === 'timeout' ? '等待模型响应超时，请重试或更换模型' : '已停止生成')
    this.name = 'StreamAbortError'
    this.reason = reason
  }
}

async function readSseStream(
  response: Response,
  onEvent: (event: StreamEvent) => void
): Promise<TextResult> {
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
  if (!response.body) {
    throw new Error('响应体为空')
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
      const lines = chunk.split('\n')
      const dataLines = lines
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.slice(5).trimStart())
      if (dataLines.length === 0) continue
      const raw = dataLines.join('\n')
      if (raw === '[DONE]') continue
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
        if (event.run_id != null) runId = event.run_id
        sawDone = true
      } else if (event.type === 'persisted') {
        runId = event.run_id
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
  let timedOut = false
  const onAbort = () => controller.abort()
  signal?.addEventListener('abort', onAbort)
  const timer = window.setTimeout(() => {
    timedOut = true
    controller.abort()
  }, LLM_TIMEOUT_MS)
  try {
    const response = await fetch(`/api/v1${path}`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(body),
      signal: controller.signal,
    })
    return await readSseStream(response, onEvent)
  } catch (err) {
    if ((err as Error).name === 'AbortError') {
      throw new StreamAbortError(timedOut ? 'timeout' : 'cancel')
    }
    throw err
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

export async function designPromptStream(
  input: {
    goal: string
    notes?: string
    provider_id?: number | null
  },
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal
): Promise<TextResult> {
  return fetchStream('/prompt/design/stream', input, onEvent, signal)
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
  return fetchStream('/prompt/optimize/stream', input, onEvent, signal)
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

export async function listOptimizeRuns(limit = 20): Promise<OptimizeRunSummary[]> {
  const { data } = await apiClient.get<OptimizeRunSummary[]>('/prompt/optimize/runs', {
    params: { limit },
  })
  return data
}

export async function getOptimizeRun(runId: number): Promise<OptimizeRunDetail> {
  const { data } = await apiClient.get<OptimizeRunDetail>(`/prompt/optimize/runs/${runId}`)
  return data
}
