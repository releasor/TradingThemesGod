import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from './client'
import { fetchNews, fetchNewsSources, refreshNews } from './news'

vi.mock('./client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

describe('news api', () => {
  beforeEach(() => vi.clearAllMocks())

  it('loads the available channel names', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: ['新浪财经', '财联社'] })

    await expect(fetchNewsSources()).resolves.toEqual(['新浪财经', '财联社'])
    expect(apiClient.get).toHaveBeenCalledWith('/news/sources')
  })

  it('filters listed and refreshed news by enabled channels', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { items: [], total: 0 } })
    vi.mocked(apiClient.post).mockResolvedValue({ data: { success: true } })

    await fetchNews(50, ['新浪财经', '财联社'], 50)
    await refreshNews(['新浪财经', '财联社'])

    expect(apiClient.get).toHaveBeenCalledWith('/news', {
      params: { limit: 50, offset: 50, sources: '新浪财经,财联社' },
    })
    expect(apiClient.post).toHaveBeenCalledWith(
      '/news/refresh',
      { sources: ['新浪财经', '财联社'] },
      { timeout: 120_000 }
    )
  })
})
