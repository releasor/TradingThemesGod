import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from '@/api/client'
import { fetchStockAiReport, generateStockAiReport } from './stock-ai-report'

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

describe('stock-ai-report api', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches cached report', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { code: '600519' } })
    await fetchStockAiReport('600519')
    expect(apiClient.get).toHaveBeenCalledWith('/stocks/600519/ai-report')
  })

  it('generates report with force and long timeout', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { code: '600519' } })
    await generateStockAiReport('600519', { force: true })
    expect(apiClient.post).toHaveBeenCalledWith(
      '/stocks/600519/ai-report',
      { force: true },
      { timeout: 300_000 }
    )
  })
})
