import { apiClient } from '@/api/client'
import { getAuthToken } from '@/stores/auth'
import { OS_LLM_TIMEOUT_MS, type OsStreamEvent } from './chat'

export type OsDailyReport = {
  id: number
  user_id: number
  report_date: string
  content: string
  provider_id: number | null
  entry_ids: number[]
  feedback_score: number | null
  feedback_note: string | null
  created_at: string
  updated_at: string
}

export async function listOsReports(): Promise<OsDailyReport[]> {
  const { data } = await apiClient.get<OsDailyReport[]>('/os/reports')
  return data
}

export async function generateOsReportStream(
  input: { report_date?: string; provider_id?: number | null },
  onEvent: (event: OsStreamEvent) => void,
  signal?: AbortSignal
): Promise<{ result: string; report_id?: number }> {
  const controller = new AbortController()
  const onAbort = () => controller.abort()
  signal?.addEventListener('abort', onAbort)
  const timer = window.setTimeout(() => controller.abort(), OS_LLM_TIMEOUT_MS)
  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    }
    const token = getAuthToken()
    if (token) headers.Authorization = `Bearer ${token}`
    const response = await fetch('/api/v1/os/reports/generate/stream', {
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
    let reportId: number | undefined
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
        if (!dataLines.length) continue
        try {
          const event = JSON.parse(dataLines.join('\n')) as OsStreamEvent & {
            report_id?: number
          }
          onEvent(event)
          if (event.type === 'delta') finalResult += event.text
          if (event.type === 'done') {
            finalResult = event.result
            reportId = event.report_id ?? event.run_id ?? undefined
            sawDone = true
          }
          if (event.type === 'error') throw new Error(event.message)
        } catch (e) {
          if (e instanceof Error && e.message !== 'Unexpected end of JSON input') {
            if ((e as Error).message.includes('请求') || (e as Error).name === 'Error') {
              if ((e as Error).message.startsWith('{')) continue
              throw e
            }
          }
        }
      }
    }
    if (!sawDone) throw new Error('流式响应异常中断')
    return { result: finalResult, report_id: reportId }
  } finally {
    window.clearTimeout(timer)
    signal?.removeEventListener('abort', onAbort)
  }
}

export async function feedbackOsReport(
  id: number,
  input: { score: number; note?: string; apply_to_prompt?: boolean }
): Promise<OsDailyReport> {
  const { data } = await apiClient.post<OsDailyReport>(`/os/reports/${id}/feedback`, input)
  return data
}
