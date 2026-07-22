import { describe, it, expect, vi } from 'vitest'

const mockGet = vi.fn()
const mockPost = vi.fn()
vi.mock('@/api/client', () => ({
  apiClient: { get: mockGet, post: mockPost },
}))

const {
  fetchThemes,
  fetchCategories,
  fetchMarketSignals,
  fetchIndicatorSignals,
  refreshThemeInsights,
} = await import('./theme')

it('refreshes theme insights', async () => {
  mockPost.mockResolvedValue({ data: { message: '题材资料已更新' } })

  await refreshThemeInsights(12)

  expect(mockPost).toHaveBeenCalledWith('/themes/12/insights/refresh', undefined, {
    timeout: 300_000,
  })
})

describe('fetchThemes', () => {
  it('calls /themes endpoint when no search query', async () => {
    mockGet.mockResolvedValue({ data: { items: [], total: 0 } })

    await fetchThemes({
      page: 1,
      page_size: 20,
      sort_by: 'heat_index',
      sort_order: 'desc',
    })

    expect(mockGet).toHaveBeenCalledWith(
      '/themes',
      expect.objectContaining({
        params: expect.objectContaining({
          page: 1,
          page_size: 20,
          sort_by: 'heat_index',
          sort_order: 'desc',
        }),
      })
    )
  })

  it('calls /themes/search endpoint when search query present', async () => {
    mockGet.mockResolvedValue({ data: { items: [], total: 0 } })

    await fetchThemes({
      page: 1,
      page_size: 20,
      sort_by: 'heat_index',
      sort_order: 'desc',
      q: 'AI',
    })

    expect(mockGet).toHaveBeenCalledWith(
      '/themes/search',
      expect.objectContaining({
        params: expect.objectContaining({
          q: 'AI',
          page: 1,
          page_size: 20,
        }),
      })
    )
  })
})

describe('fetchCategories', () => {
  it('calls /themes/categories endpoint', async () => {
    mockGet.mockResolvedValue({ data: { categories: ['科技', '医药'] } })

    const result = await fetchCategories()

    expect(mockGet).toHaveBeenCalledWith('/themes/categories')
    expect(result).toEqual({ categories: ['科技', '医药'] })
  })
})

describe('fetchMarketSignals', () => {
  it('calls /themes/market-signals endpoint', async () => {
    const response = { items: [], limit: 0 }
    mockGet.mockResolvedValue({ data: response })

    const result = await fetchMarketSignals()

    expect(mockGet).toHaveBeenCalledWith('/themes/market-signals')
    expect(result).toEqual(response)
  })

  it('normalizes decimal strings from the API into numbers', async () => {
    mockGet.mockResolvedValue({
      data: {
        items: [
          {
            id: 81,
            name: '昨日涨停',
            code: 'BK0815',
            heat_index: '9.32',
            rise_fall_pct: '6.8800',
            stock_count: 46,
          },
        ],
        limit: 1,
      },
    })

    const result = await fetchMarketSignals()

    expect(result.items[0]).toEqual(
      expect.objectContaining({
        heat_index: 9.32,
        rise_fall_pct: 6.88,
      })
    )
  })
})

describe('fetchIndicatorSignals', () => {
  it('calls /themes/indicator-signals endpoint', async () => {
    const response = { items: [], limit: 0 }
    mockGet.mockResolvedValue({ data: response })

    const result = await fetchIndicatorSignals()

    expect(mockGet).toHaveBeenCalledWith('/themes/indicator-signals')
    expect(result).toEqual(response)
  })
})
