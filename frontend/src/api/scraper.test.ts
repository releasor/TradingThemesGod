import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockGet = vi.fn()
const mockPost = vi.fn()

vi.mock('@/api/client', () => ({
  apiClient: {
    get: mockGet,
    post: mockPost,
  },
}))

const {
  fetchLatestSuccessfulRun,
  fetchDashboardScraperSources,
  refreshThemeQuotes,
  runScraperAndWait,
  runScraperWithFallback,
  startScraperRace,
  fetchScraperRace,
  cancelScraperRace,
  runScraperRaceAndWait,
  effectiveRaceCollectPct,
  formatRaceSourcesStatus,
  mapRaceProgressToDashboardPct,
  shortenRaceSourceError,
} = await import('./scraper')

const sampleRace = (overrides: Partial<{
  race_id: string
  status: string
  phase: string
  progress_pct: number
  winner: string | null
  error: string | null
  items_scraped: number | null
}> = {}) => ({
  race_id: 'race-abc',
  status: 'racing',
  phase: 'collecting',
  progress_pct: 0,
  sources: [
    { id: 'eastmoney', status: 'running', progress_pct: 0, error: null },
    { id: 'akshare', status: 'running', progress_pct: 0, error: null },
  ],
  winner: null,
  error: null,
  items_scraped: null,
  ...overrides,
})

describe('scraper API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns dashboard scraper sources', async () => {
    mockGet.mockResolvedValue({
      data: {
        sources: [
          {
            id: 'eastmoney',
            label: '东方财富',
            description: '题材列表',
            dashboard_selectable: true,
            is_default: true,
          },
          {
            id: 'akshare',
            label: 'AKShare',
            description: 'A 股行情',
            dashboard_selectable: true,
            is_default: false,
          },
        ],
        count: 2,
      },
    })

    const result = await fetchDashboardScraperSources()

    expect(mockGet).toHaveBeenCalledWith('/scraper/sources', {
      params: { dashboard_only: true },
    })
    expect(result).toHaveLength(2)
    expect(result[0].id).toBe('eastmoney')
  })

  it('returns the latest successful run for a source', async () => {
    mockGet.mockResolvedValue({
      data: {
        runs: [
          {
            run_id: 1,
            source: 'eastmoney',
            status: 'completed',
            started_at: '2026-07-15T01:00:00Z',
            finished_at: '2026-07-15T01:02:00Z',
            items_scraped: 20,
            error_message: null,
          },
        ],
        count: 1,
      },
    })

    const result = await fetchLatestSuccessfulRun('eastmoney')

    expect(mockGet).toHaveBeenCalledWith('/scraper/runs', {
      params: { source: 'eastmoney', status: 'completed', limit: 5 },
    })
    expect(result?.run_id).toBe(1)
  })

  it('starts a scraper and waits until it completes', async () => {
    mockPost.mockResolvedValue({
      data: {
        run_id: 3,
        source: 'eastmoney',
        status: 'running',
        started_at: '2026-07-16T02:00:00Z',
        finished_at: null,
        items_scraped: 0,
        error_message: null,
      },
    })
    mockGet
      .mockResolvedValueOnce({ data: { run_id: 3, status: 'running' } })
      .mockResolvedValueOnce({
        data: {
          run_id: 3,
          source: 'eastmoney',
          status: 'completed',
          started_at: '2026-07-16T02:00:00Z',
          finished_at: '2026-07-16T02:03:00Z',
          items_scraped: 120,
          error_message: null,
        },
      })

    const result = await runScraperAndWait('eastmoney', { pollInterval: 0 })

    expect(mockPost).toHaveBeenCalledWith(
      '/scraper/run/eastmoney',
      { params: {} },
      expect.objectContaining({ signal: undefined })
    )
    expect(mockGet).toHaveBeenCalledTimes(2)
    expect(result.status).toBe('completed')
  })

  it('returns the failed scraper result', async () => {
    mockPost.mockResolvedValue({ data: { run_id: 4, status: 'running' } })
    mockGet.mockResolvedValue({
      data: {
        run_id: 4,
        status: 'failed',
        error_message: '数据源不可用',
      },
    })

    const result = await runScraperAndWait('eastmoney', { pollInterval: 0 })

    expect(result.status).toBe('failed')
    expect(result.error_message).toBe('数据源不可用')
  })

  it('does not fall back to next source after timeout', async () => {
    mockPost.mockResolvedValue({
      data: {
        run_id: 5,
        source: 'eastmoney',
        status: 'running',
        started_at: '2026-07-16T02:00:00Z',
        finished_at: null,
        items_scraped: 0,
        error_message: null,
      },
    })
    mockGet.mockResolvedValue({
      data: {
        run_id: 5,
        source: 'eastmoney',
        status: 'running',
        started_at: '2026-07-16T02:00:00Z',
        finished_at: null,
        items_scraped: 0,
        error_message: null,
      },
    })

    await expect(
      runScraperWithFallback(['eastmoney', 'akshare'], {
        pollInterval: 0,
        timeout: 1,
      })
    ).rejects.toThrow(/超时/)

    expect(mockPost).toHaveBeenCalledTimes(1)
    expect(mockPost).toHaveBeenCalledWith(
      '/scraper/run/eastmoney',
      { params: {} },
      expect.objectContaining({ signal: undefined })
    )
  })

  it('passes AbortSignal to refreshThemeQuotes', async () => {
    mockPost.mockResolvedValue({
      data: {
        trade_date: '2026-07-21',
        themes_updated: 42,
        refreshed_at: '2026-07-21T10:00:00Z',
      },
    })

    const signal = new AbortController().signal
    await refreshThemeQuotes(signal)

    expect(mockPost).toHaveBeenCalledWith(
      '/scraper/refresh-quotes',
      null,
      expect.objectContaining({ signal, timeout: 120_000 })
    )
  })

  it('starts a scraper race', async () => {
    mockPost.mockResolvedValue({ data: sampleRace() })

    const result = await startScraperRace()

    expect(mockPost).toHaveBeenCalledWith(
      '/scraper/run-race',
      null,
      expect.objectContaining({ signal: undefined, timeout: 60_000 })
    )
    expect(result.race_id).toBe('race-abc')
    expect(result.status).toBe('racing')
  })

  it('fetches scraper race status', async () => {
    mockGet.mockResolvedValue({
      data: sampleRace({ progress_pct: 42, status: 'racing' }),
    })

    const result = await fetchScraperRace('race-abc')

    expect(mockGet).toHaveBeenCalledWith('/scraper/race/race-abc', {
      signal: undefined,
      timeout: 60_000,
    })
    expect(result.progress_pct).toBe(42)
  })

  it('cancels scraper race', async () => {
    mockPost.mockResolvedValue({
      data: sampleRace({ status: 'cancelled', phase: 'done', progress_pct: 10 }),
    })

    const result = await cancelScraperRace('race-abc')

    expect(mockPost).toHaveBeenCalledWith(
      '/scraper/race/race-abc/cancel',
      null,
      expect.objectContaining({ signal: undefined, timeout: 60_000 })
    )
    expect(result.status).toBe('cancelled')
  })

  it('runs scraper race and waits until completed', async () => {
    mockPost.mockResolvedValueOnce({ data: sampleRace() })
    mockGet
      .mockResolvedValueOnce({ data: sampleRace({ progress_pct: 40 }) })
      .mockResolvedValueOnce({
        data: sampleRace({
          status: 'completed',
          phase: 'done',
          progress_pct: 100,
          winner: 'eastmoney',
          items_scraped: 120,
        }),
      })

    const onProgress = vi.fn()
    const result = await runScraperRaceAndWait({ pollInterval: 0, onProgress })

    expect(mockPost).toHaveBeenCalledWith(
      '/scraper/run-race',
      null,
      expect.objectContaining({ signal: undefined, timeout: 60_000 })
    )
    expect(mockGet).toHaveBeenCalledTimes(2)
    expect(onProgress).toHaveBeenCalledTimes(3)
    expect(result.status).toBe('completed')
    expect(result.winner).toBe('eastmoney')
  })

  it('skips transient poll timeouts and continues waiting', async () => {
    mockPost.mockResolvedValueOnce({ data: sampleRace() })
    const timeoutError = Object.assign(new Error('timeout of 10000ms exceeded'), {
      code: 'ECONNABORTED',
    })
    mockGet
      .mockRejectedValueOnce(timeoutError)
      .mockResolvedValueOnce({
        data: sampleRace({
          status: 'completed',
          phase: 'done',
          progress_pct: 100,
          winner: 'eastmoney',
          items_scraped: 50,
        }),
      })

    const result = await runScraperRaceAndWait({ pollInterval: 0 })

    expect(result.status).toBe('completed')
    expect(mockGet).toHaveBeenCalledTimes(2)
  })

  it('skips transient 5xx poll errors and continues waiting', async () => {
    mockPost.mockResolvedValueOnce({ data: sampleRace() })
    const serverError = Object.assign(new Error('Request failed with status code 500'), {
      response: { status: 500 },
    })
    mockGet
      .mockRejectedValueOnce(serverError)
      .mockResolvedValueOnce({
        data: sampleRace({
          status: 'completed',
          phase: 'done',
          progress_pct: 100,
          winner: 'ths',
          items_scraped: 374,
        }),
      })

    const result = await runScraperRaceAndWait({ pollInterval: 0 })

    expect(result.status).toBe('completed')
    expect(result.winner).toBe('ths')
    expect(mockGet).toHaveBeenCalledTimes(2)
  })

  it('stops with a clear message when race poll returns 404', async () => {
    mockPost.mockResolvedValueOnce({ data: sampleRace() })
    const missing = Object.assign(new Error('Request failed with status code 404'), {
      response: { status: 404 },
    })
    mockGet.mockRejectedValueOnce(missing)

    await expect(runScraperRaceAndWait({ pollInterval: 0 })).rejects.toThrow(
      /服务可能已重启/
    )
  })

  it('calls cancelScraperRace when aborted during wait', async () => {
    mockPost
      .mockResolvedValueOnce({ data: sampleRace() })
      .mockResolvedValueOnce({
        data: sampleRace({ status: 'cancelled', phase: 'done' }),
      })
    mockGet.mockImplementation(
      () =>
        new Promise(() => {
          /* never resolves until abort */
        })
    )

    const controller = new AbortController()
    const waitPromise = runScraperRaceAndWait({
      pollInterval: 0,
      signal: controller.signal,
    })

    await Promise.resolve()
    controller.abort()

    await expect(waitPromise).rejects.toMatchObject({ name: 'AbortError' })
    expect(mockPost).toHaveBeenCalledWith(
      '/scraper/race/race-abc/cancel',
      null,
      expect.any(Object)
    )
  })
})

describe('race progress helpers', () => {
  const label = (id: string) => (id === 'akshare' ? 'AKShare' : '东方财富')

  it('effectiveRaceCollectPct ignores completed sources while others run', () => {
    expect(
      effectiveRaceCollectPct([
        { id: 'akshare', status: 'completed', progress_pct: 100 },
        { id: 'eastmoney', status: 'running', progress_pct: 12 },
      ])
    ).toBe(12)
  })

  it('effectiveRaceCollectPct returns 100 when all sources completed', () => {
    expect(
      effectiveRaceCollectPct([
        { id: 'akshare', status: 'completed', progress_pct: 100 },
        { id: 'eastmoney', status: 'completed', progress_pct: 100 },
      ])
    ).toBe(100)
  })

  it('mapRaceProgressToDashboardPct caps collect phase at 70%', () => {
    expect(
      mapRaceProgressToDashboardPct({
        phase: 'collecting',
        progress_pct: 100,
        sources: [
          { id: 'akshare', status: 'completed', progress_pct: 100 },
          { id: 'eastmoney', status: 'running', progress_pct: 40 },
        ],
      })
    ).toBe(28)
  })

  it('formatRaceSourcesStatus shows committed source while others still collect', () => {
    const { pendingLabel, message } = formatRaceSourcesStatus(
      {
        phase: 'collecting',
        status: 'racing',
        progress_pct: 100,
        winner: null,
        sources: [
          { id: 'akshare', status: 'completed', progress_pct: 100 },
          { id: 'eastmoney', status: 'running', progress_pct: 15 },
        ],
      },
      '23 秒',
      label
    )

    expect(pendingLabel).toBe('AKShare 已写入 · 东方财富 15%')
    expect(message).toMatch(/AKShare 已写入，可切换查看/)
    expect(message).toMatch(/东方财富 仍在采集/)
    expect(message).toMatch(/东方财富 采集中 15%/)
  })

  it('shortenRaceSourceError compresses connect timeouts', () => {
    expect(
      shortenRaceSourceError(
        "HTTPSConnectionPool(host='79.push2.eastmoney.com', port=443): Max retries exceeded (Caused by ConnectTimeoutError(...))"
      )
    ).toBe('连接超时（79.push2.eastmoney.com）')
  })

  it('shortenRaceSourceError compresses remote disconnects', () => {
    expect(
      shortenRaceSourceError(
        "('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))"
      )
    ).toBe('上游提前断开连接')
  })

  it('formatRaceSourcesStatus does not duplicate failed source text', () => {
    const { message } = formatRaceSourcesStatus(
      {
        phase: 'collecting',
        status: 'racing',
        progress_pct: 10,
        winner: null,
        sources: [
          {
            id: 'akshare',
            status: 'failed',
            progress_pct: 100,
            error: "('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))",
          },
          { id: 'eastmoney', status: 'running', progress_pct: 10 },
        ],
      },
      '43 秒',
      label
    )

    expect(message).toMatch(/AKShare 失败：上游提前断开连接/)
    expect(message).toMatch(/东方财富 采集中 10%/)
    expect(message.match(/上游提前断开连接/g)?.length).toBe(1)
  })

  it('formatRaceSourcesStatus surfaces failed source reasons', () => {
    const { pendingLabel, message } = formatRaceSourcesStatus(
      {
        phase: 'done',
        status: 'failed',
        progress_pct: 100,
        winner: null,
        error: '全部数据源失败 — eastmoney: 连接超时；akshare: 连接超时',
        sources: [
          {
            id: 'eastmoney',
            status: 'failed',
            progress_pct: 100,
            error: "ConnectTimeoutError host='push2.eastmoney.com'",
          },
          {
            id: 'akshare',
            status: 'failed',
            progress_pct: 100,
            error: "ConnectTimeoutError host='79.push2.eastmoney.com'",
          },
        ],
      },
      '43 秒',
      label
    )

    expect(pendingLabel).toBe('多源竞速失败')
    expect(message).toMatch(/全量更新失败：全部数据源失败/)
    expect(message).toMatch(/连接超时/)
  })
})
