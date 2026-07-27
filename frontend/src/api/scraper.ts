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
export async function refreshThemeQuotes(): Promise<ThemeQuotesRefreshResult> {
  const { data } = await apiClient.post<ThemeQuotesRefreshResult>(
    '/scraper/refresh-quotes',
    null,
    { timeout: 120_000 }
  )
  return data
}

/** 触发采集任务并轮询到最终状态。 */
export async function runScraperAndWait(
  source: string,
  { pollInterval = 2000, timeout = 10 * 60 * 1000 }: WaitOptions = {}
): Promise<ScraperRun> {
  const { data: startedRun } = await apiClient.post<ScraperRun>(`/scraper/run/${source}`, {
    params: {},
  })

  if (startedRun.status !== 'running') return startedRun

  const deadline = Date.now() + timeout
  while (Date.now() <= deadline) {
    await sleep(pollInterval)
    const { data: run } = await apiClient.get<ScraperRun>(
      `/scraper/status/${startedRun.run_id}`
    )
    if (run.status !== 'running') return run
  }

  throw new Error('数据更新超时，请稍后查看更新结果')
}

/** 按顺序尝试多个数据源，前一个失败或超时后自动切换。 */
export async function runScraperWithFallback(
  sources: string[],
  { pollInterval = 2000, timeout = 3 * 60 * 1000 }: WaitOptions = {}
): Promise<ScraperRunWithAttempts> {
  const attemptedSources: string[] = []
  let lastError: Error | null = null

  for (const source of sources) {
    attemptedSources.push(source)
    try {
      const run = await runScraperAndWait(source, { pollInterval, timeout })
      if (run.status === 'completed') {
        return { ...run, attempted_sources: attemptedSources }
      }
      lastError = new Error(run.error_message || `${source} 全量更新失败`)
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error))
    }
  }

  throw lastError ?? new Error('全量更新失败')
}
