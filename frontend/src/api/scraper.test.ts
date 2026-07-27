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
} = await import('./scraper')

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

    expect(mockPost).toHaveBeenCalledWith('/scraper/run/eastmoney', { params: {} })
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
    expect(mockPost).toHaveBeenCalledWith('/scraper/run/eastmoney', { params: {} })
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
})
