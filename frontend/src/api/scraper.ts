/** 爬虫任务 API 客户端。 */

import { apiClient } from '@/api/client'

export type ScraperRunStatus = 'running' | 'completed' | 'failed'

export interface ScraperRun {
  run_id: number
  source: string
  status: ScraperRunStatus
  started_at: string
  finished_at: string | null
  items_scraped: number
  error_message: string | null
}

export interface ScraperSource {
  id: string
  label: string
  description: string
  dashboard_selectable: boolean
  is_default: boolean
}

interface ScraperRunListResponse {
  runs: ScraperRun[]
  count: number
}

interface ScraperSourceListResponse {
  sources: ScraperSource[]
  count: number
}

interface WaitOptions {
  pollInterval?: number
  timeout?: number
  signal?: AbortSignal
}

export interface ScraperRunWithAttempts extends ScraperRun {
  attempted_sources: string[]
}

export interface ThemeQuotesRefreshResult {
  trade_date: string | null
  themes_updated: number
  refreshed_at: string
}

const sleep = (delay: number) => new Promise((resolve) => setTimeout(resolve, delay))

/** 获取看板可选的爬虫数据源列表。 */
export async function fetchDashboardScraperSources(): Promise<ScraperSource[]> {
  const { data } = await apiClient.get<ScraperSourceListResponse>('/scraper/sources', {
    params: { dashboard_only: true },
  })
  return data.sources
}

/** 获取指定数据源最近一次成功完成的采集记录。 */
export async function fetchLatestSuccessfulRun(source: string): Promise<ScraperRun | null> {
  const { data } = await apiClient.get<ScraperRunListResponse>('/scraper/runs', {
    params: { source, status: 'completed', limit: 5 },
  })
  return data.runs[0] ?? null
}

/** 快刷题材列表涨跌幅/热度，不触发全量成分股采集。 */
export async function refreshThemeQuotes(signal?: AbortSignal): Promise<ThemeQuotesRefreshResult> {
  const { data } = await apiClient.post<ThemeQuotesRefreshResult>(
    '/scraper/refresh-quotes',
    null,
    { timeout: 120_000, signal }
  )
  return data
}

function throwIfAborted(signal?: AbortSignal): void {
  if (signal?.aborted) {
    const err = new Error('Aborted')
    err.name = 'AbortError'
    throw err
  }
}

async function pollScraperRun(
  runId: number,
  { pollInterval = 2000, timeout = 10 * 60 * 1000, signal }: WaitOptions = {}
): Promise<ScraperRun> {
  const deadline = Date.now() + timeout
  while (Date.now() <= deadline) {
    throwIfAborted(signal)
    await sleep(pollInterval)
    throwIfAborted(signal)
    const { data: run } = await apiClient.get<ScraperRun>(`/scraper/status/${runId}`, { signal })
    if (run.status !== 'running') return run
  }
  throw new Error(
    `数据更新超时（任务 #${runId} 可能仍在后台运行）。请稍后再点「刷新」；全量采集结束前轻量刷新会被暂时锁定。`
  )
}

/** 触发采集任务并轮询到最终状态。已在运行时后端会返回同一 run，直接附着轮询。 */
export async function runScraperAndWait(
  source: string,
  { pollInterval = 2000, timeout = 20 * 60 * 1000, signal }: WaitOptions = {}
): Promise<ScraperRun> {
  throwIfAborted(signal)
  const { data: startedRun } = await apiClient.post<ScraperRun>(
    `/scraper/run/${source}`,
    { params: {} },
    { signal }
  )

  if (startedRun.status !== 'running') return startedRun
  return pollScraperRun(startedRun.run_id, { pollInterval, timeout, signal })
}

/** 按顺序尝试多个数据源；超时不切源（避免误报成功且后台任务仍锁住轻量刷新）。 */
export async function runScraperWithFallback(
  sources: string[],
  { pollInterval = 2000, timeout = 20 * 60 * 1000, signal }: WaitOptions = {}
): Promise<ScraperRunWithAttempts> {
  const attemptedSources: string[] = []
  let lastError: Error | null = null

  for (const source of sources) {
    throwIfAborted(signal)
    attemptedSources.push(source)
    try {
      const run = await runScraperAndWait(source, { pollInterval, timeout, signal })
      if (run.status === 'completed') {
        return { ...run, attempted_sources: attemptedSources }
      }
      lastError = new Error(run.error_message || `${source} 全量更新失败`)
    } catch (error) {
      if (signal?.aborted || (error instanceof Error && error.name === 'AbortError')) {
        throw error
      }
      const err = error instanceof Error ? error : new Error(String(error))
      // 超时：该源多半仍在跑，切源会让界面显示成功但 refresh-quotes 继续 409
      if (err.message.includes('超时')) {
        throw err
      }
      lastError = err
    }
  }

  throw lastError ?? new Error('全量更新失败')
}
