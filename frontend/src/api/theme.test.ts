import { describe, it, expect, vi } from 'vitest'

// Mock axios before importing the module
const mockGet = vi.fn()
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: mockGet,
    })),
  },
}))

// Import after mock is set up
const { fetchThemes, fetchCategories } = await import('./theme')

describe('fetchThemes', () => {
  it('calls /themes endpoint when no search query', async () => {
    mockGet.mockResolvedValue({ data: { items: [], total: 0 } })

    await fetchThemes({
      page: 1,
      page_size: 20,
      sort_by: 'heat_index',
      sort_order: 'desc',
    })

    expect(mockGet).toHaveBeenCalledWith('/themes', expect.objectContaining({
      params: expect.objectContaining({
        page: 1,
        page_size: 20,
        sort_by: 'heat_index',
        sort_order: 'desc',
      }),
    }))
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

    expect(mockGet).toHaveBeenCalledWith('/themes/search', expect.objectContaining({
      params: expect.objectContaining({
        q: 'AI',
        page: 1,
        page_size: 20,
      }),
    }))
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
