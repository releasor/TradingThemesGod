import { describe, it, expect, vi } from 'vitest'

// Mock the shared API client
vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
  },
}))

// Import after mock is set up
const { fetchStockDetail } = await import('./stock')
const { apiClient } = await import('@/api/client')

describe('fetchStockDetail', () => {
  it('calls /stocks/{code} endpoint with correct code', async () => {
    const mockResponse = {
      data: {
        code: '000001',
        name: '平安银行',
        industry: '银行',
        market_cap: 2000000000,
        current_price: 12.50,
        rise_fall_pct: 1.5,
        exchange: 'SZSE',
        events: [],
      },
    }
    vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

    const result = await fetchStockDetail('000001')

    expect(apiClient.get).toHaveBeenCalledWith('/stocks/000001')
    expect(result).toEqual(mockResponse.data)
  })

  it('returns stock data with events', async () => {
    const mockResponse = {
      data: {
        code: '600519',
        name: '贵州茅台',
        industry: '白酒',
        market_cap: 2000000000000,
        current_price: 1800.00,
        rise_fall_pct: -0.5,
        exchange: 'SSE',
        events: [
          {
            id: 1,
            title: '贵州茅台发布年报',
            content: '...',
            source: '新浪财经',
            event_type: 'news',
            published_at: '2026-01-15T10:00:00Z',
          },
        ],
      },
    }
    vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

    const result = await fetchStockDetail('600519')

    expect(apiClient.get).toHaveBeenCalledWith('/stocks/600519')
    expect(result.events).toHaveLength(1)
    expect(result.events[0].title).toBe('贵州茅台发布年报')
  })
})
