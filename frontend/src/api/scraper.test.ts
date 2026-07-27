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
      expect.objectContaining({ signal: undefined })
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
      expect.objectContaining({ signal: undefined })
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
      expect.objectContaining({ signal: undefined })
    )
    expect(mockGet).toHaveBeenCalledTimes(2)
    expect(onProgress).toHaveBeenCalledTimes(3)
    expect(result.status).toBe('completed')
    expect(result.winner).toBe('eastmoney')
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
