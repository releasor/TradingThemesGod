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

export interface ScraperRaceSource {
  id: string
  status: string
  progress_pct: number
  error?: string | null
}

export interface ScraperRace {
  race_id: string
  status: string
  phase: string
  progress_pct: number
  sources: ScraperRaceSource[]
  winner: string | null
  error: string | null
  items_scraped?: number | null
}

interface RaceWaitOptions {
  pollInterval?: number
  timeout?: number
  signal?: AbortSignal
  onProgress?: (race: ScraperRace) => void
}

const RACE_IN_PROGRESS = new Set(['racing', 'committing'])

/** 单次竞速 HTTP 请求超时（全局 axios 默认仅 10s，全量采集期间轮询会被拖死） */
const RACE_REQUEST_TIMEOUT_MS = 60_000
/** 全量竞速整体等待上限（东财成分股采集常需 20–40 分钟） */
const RACE_WAIT_TIMEOUT_MS = 45 * 60 * 1000

const sleep = (delay: number) => new Promise((resolve) => setTimeout(resolve, delay))

/** 竞速采集阶段的有效进度：仅统计仍在 running 的源，避免 AKShare 先到 100% 误导整体进度。 */
export function effectiveRaceCollectPct(sources: ScraperRaceSource[]): number {
  const running = sources.filter((item) => item.status === 'running')
  if (running.length > 0) {
    return Math.max(...running.map((item) => item.progress_pct))
  }
  if (sources.some((item) => item.status === 'completed')) {
    return 100
  }
  return 0
}

export function mapRaceProgressToDashboardPct(race: Pick<ScraperRace, 'phase' | 'progress_pct' | 'sources'>): number {
  const collectPct =
    race.phase === 'collecting' && race.sources?.length
      ? effectiveRaceCollectPct(race.sources)
      : race.progress_pct
  return Math.round(Math.min(70, Math.max(0, collectPct) * 0.7))
}

/** 将竞速源底层异常压缩为可读短句。 */
export function shortenRaceSourceError(error: string | null | undefined, limit = 120): string {
  const text = (error ?? '').trim()
  if (!text) return '未知错误'
  const lower = text.toLowerCase()
  if (lower.includes('remotedisconnected') || lower.includes('connection aborted')) {
    return '上游提前断开连接'
  }
  if (
    lower.includes('connecttimeout') ||
    lower.includes('connect timeout') ||
    lower.includes('timed out')
  ) {
    const hostMatch = text.match(/host=['"]?([^'",\s)]+)/i)
    return hostMatch ? `连接超时（${hostMatch[1]}）` : '连接超时'
  }
  if (lower.includes('max retries exceeded')) {
    return '请求重试耗尽（上游不可达）'
  }
  if (lower.includes('proxyerror') || (lower.includes('proxy') && lower.includes('error'))) {
    return '代理/网络错误'
  }
  return text.length <= limit ? text : `${text.slice(0, limit - 1)}…`
}

export function formatRaceSourcesStatus(
  race: Pick<ScraperRace, 'phase' | 'status' | 'progress_pct' | 'winner' | 'sources' | 'error'>,
  elapsed: string,
  sourceLabel: (id: string) => string
): { pendingLabel: string; message: string } {
  const sources = race.sources ?? []
  const running = sources.filter((item) => item.status === 'running')
  const completed = sources.filter((item) => item.status === 'completed')
  const failed = sources.filter((item) => item.status === 'failed')

  const partFor = (item: ScraperRaceSource) => {
    const label = sourceLabel(item.id)
    if (item.status === 'running') {
      return `${label} 采集中 ${Math.round(item.progress_pct)}%`
    }
    if (item.status === 'completed') {
      return `${label} 已完成`
    }
    if (item.status === 'failed') {
      return `${label} 失败：${shortenRaceSourceError(item.error)}`
    }
    if (item.status === 'cancelled') {
      return `${label} 已取消`
    }
    return `${label} 等待中`
  }

  const parts = sources.map(partFor).join(' · ')
  const winnerLabel = race.winner ? sourceLabel(race.winner) : null
  const pct = Math.round(race.progress_pct)
  const failedSummary =
    failed.length > 0
      ? failed
          .map((item) => `${sourceLabel(item.id)}：${shortenRaceSourceError(item.error)}`)
          .join('；')
      : ''

  if (race.phase === 'committing') {
    return {
      pendingLabel: '落库',
      message: winnerLabel
        ? `已选定 ${winnerLabel}，落库中 ${pct}%（已耗时 ${elapsed}）...`
        : `落库中 ${pct}%（已耗时 ${elapsed}）...`,
    }
  }

  if (race.status === 'failed' || (failed.length > 0 && running.length === 0 && completed.length === 0)) {
    const detail = race.error?.trim() || failedSummary || parts
    return {
      pendingLabel: '多源竞速失败',
      message: `全量更新失败：${detail}（已耗时 ${elapsed}）`,
    }
  }

  if (running.length === 1 && completed.length > 0) {
    const active = running[0]
    const activeLabel = sourceLabel(active.id)
    const doneLabels = completed.map((item) => sourceLabel(item.id)).join('、')
    return {
      pendingLabel: `等待 ${activeLabel} ${Math.round(active.progress_pct)}%`,
      message: `${doneLabels} 已采完，正在等待 ${activeLabel} 完整采集（含成分股）。${parts}（已耗时 ${elapsed}）`,
    }
  }

  if (running.length > 0) {
    const active = [...running].sort((a, b) => b.progress_pct - a.progress_pct)[0]
    return {
      pendingLabel: `竞速 · ${sourceLabel(active.id)} ${Math.round(active.progress_pct)}%`,
      message: `多源竞速中：${parts}（已耗时 ${elapsed}）...`,
    }
  }

  return {
    pendingLabel: '多源竞速',
    message: `多源竞速中 ${pct}%（已耗时 ${elapsed}）...`,
  }
}

function isAxiosTimeoutError(error: unknown): boolean {
  const err = error as { code?: string; message?: string }
  return err?.code === 'ECONNABORTED' || Boolean(err?.message?.includes('timeout'))
}

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

/** 启动全量多源竞速。 */
export async function startScraperRace(signal?: AbortSignal): Promise<ScraperRace> {
  const { data } = await apiClient.post<ScraperRace>('/scraper/run-race', null, {
    signal,
    timeout: RACE_REQUEST_TIMEOUT_MS,
  })
  return data
}

/** 查询全量竞速状态与进度。 */
export async function fetchScraperRace(raceId: string, signal?: AbortSignal): Promise<ScraperRace> {
  const { data } = await apiClient.get<ScraperRace>(`/scraper/race/${raceId}`, {
    signal,
    timeout: RACE_REQUEST_TIMEOUT_MS,
  })
  return data
}

/** 取消全量竞速。 */
export async function cancelScraperRace(raceId: string, signal?: AbortSignal): Promise<ScraperRace> {
  const { data } = await apiClient.post<ScraperRace>(
    `/scraper/race/${raceId}/cancel`,
    null,
    { signal, timeout: RACE_REQUEST_TIMEOUT_MS }
  )
  return data
}

/** 启动全量竞速并轮询至终态；AbortSignal 触发时尽力取消后端竞速。 */
export async function runScraperRaceAndWait(
  options: RaceWaitOptions = {}
): Promise<ScraperRace> {
  const {
    pollInterval = 2000,
    timeout = RACE_WAIT_TIMEOUT_MS,
    signal,
    onProgress,
  } = options
  throwIfAborted(signal)

  const started = await startScraperRace(signal)
  onProgress?.(started)

  if (!RACE_IN_PROGRESS.has(started.status)) {
    return started
  }

  const raceId = started.race_id
  const cancelBestEffort = () => {
    void cancelScraperRace(raceId).catch(() => {
      /* best-effort */
    })
  }

  if (signal?.aborted) {
    cancelBestEffort()
    throwIfAborted(signal)
  }

  signal?.addEventListener('abort', cancelBestEffort, { once: true })

  try {
    const deadline = Date.now() + timeout
    while (Date.now() <= deadline) {
      throwIfAborted(signal)
      await sleep(pollInterval)
      throwIfAborted(signal)
      try {
        const race = await fetchScraperRace(raceId, signal)
        onProgress?.(race)
        if (!RACE_IN_PROGRESS.has(race.status)) {
          return race
        }
      } catch (error) {
        if (signal?.aborted || (error instanceof Error && error.name === 'AbortError')) {
          throw error
        }
        // 采集高峰时偶发单次轮询超时：跳过本轮，不中断整次全量
        if (isAxiosTimeoutError(error) && Date.now() + pollInterval <= deadline) {
          continue
        }
        throw error
      }
    }
    throw new Error(
      `全量更新超时（竞速任务 ${raceId} 可能仍在后台运行，已等待 ${Math.round(timeout / 60000)} 分钟）。可稍后点「刷新」查看结果，或重新全量更新。`
    )
  } finally {
    signal?.removeEventListener('abort', cancelBestEffort)
  }
}
