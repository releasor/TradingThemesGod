import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '@/api/client'

import {
  ensureReviewReport,
  fetchReviewDay,
  fetchReviewDays,
  fetchReviewReport,
  fetchReviewTheme,
} from './review'

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

describe('review api', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches review days without params', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { items: [] } })
    await fetchReviewDays()
    expect(apiClient.get).toHaveBeenCalledWith('/review/days', { params: {} })
  })

  it('fetches review days with from/to params', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { items: ['2026-07-24'] } })
    await fetchReviewDays({ from: '2026-07-01', to: '2026-07-24' })
    expect(apiClient.get).toHaveBeenCalledWith('/review/days', {
      params: { from: '2026-07-01', to: '2026-07-24' },
    })
  })

  it('fetches review day by date', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { trade_date: '2026-07-24' } })
    await fetchReviewDay('2026-07-24')
    expect(apiClient.get).toHaveBeenCalledWith('/review/days/2026-07-24')
  })

  it('fetches review theme with default days', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { theme_id: 1 } })
    await fetchReviewTheme(42)
    expect(apiClient.get).toHaveBeenCalledWith('/review/themes/42', { params: { days: 10 } })
  })

  it('fetches review theme with custom days', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { theme_id: 1 } })
    await fetchReviewTheme(42, 20)
    expect(apiClient.get).toHaveBeenCalledWith('/review/themes/42', { params: { days: 20 } })
  })

  it('fetches review report by date', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { trade_date: '2026-07-24' } })
    await fetchReviewReport('2026-07-24')
    expect(apiClient.get).toHaveBeenCalledWith('/review/days/2026-07-24/report')
  })

  it('returns null when review report payload is null', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: null })
    await expect(fetchReviewReport('2026-07-24')).resolves.toBeNull()
  })

  it('ensures review report with 60s timeout', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { status: 'pending' } })
    await ensureReviewReport('2026-07-24')
    expect(apiClient.post).toHaveBeenCalledWith(
      '/review/days/2026-07-24/report/ensure',
      null,
      { timeout: 60_000 }
    )
  })
})
