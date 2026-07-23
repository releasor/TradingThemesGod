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
    params: { source, limit: 20 },
  })
  return data.runs.find((run) => run.status === 'completed') ?? null
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
