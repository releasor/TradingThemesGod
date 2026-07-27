import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '@/api/client'

import {
  ensureCatalystClassify,
  fetchCatalystFeed,
  fetchCatalystThemeSummary,
} from './catalysts'

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

describe('catalysts api', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches feed without params', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { items: [], total: 0 } })
    await fetchCatalystFeed()
    expect(apiClient.get).toHaveBeenCalledWith('/catalysts/feed', { params: {} })
  })

  it('fetches feed with filters', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { items: [], total: null } })
    await fetchCatalystFeed({
      freshness: 'new',
      actor_type: 'policy',
      theme_id: 7,
      q: '机器人',
      from: '2026-07-01',
      to: '2026-07-26',
      limit: 20,
      offset: 10,
    })
    expect(apiClient.get).toHaveBeenCalledWith('/catalysts/feed', {
      params: {
        freshness: 'new',
        actor_type: 'policy',
        theme_id: 7,
        q: '机器人',
        from: '2026-07-01',
        to: '2026-07-26',
        limit: 20,
        offset: 10,
      },
    })
  })

  it('fetches theme summary by id', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { theme_id: 42 } })
    await fetchCatalystThemeSummary(42)
    expect(apiClient.get).toHaveBeenCalledWith('/catalysts/themes/42/summary')
  })

  it('ensures classify with defaults', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { classified_rules: 3, model_queued: false },
    })
    await ensureCatalystClassify()
    expect(apiClient.post).toHaveBeenCalledWith('/catalysts/classify/ensure', null, {
      params: { days: 7, use_model: false },
      timeout: 60_000,
    })
  })

  it('ensures classify with custom params', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { classified_rules: 1, model_queued: true },
    })
    await ensureCatalystClassify({ days: 14, use_model: true })
    expect(apiClient.post).toHaveBeenCalledWith('/catalysts/classify/ensure', null, {
      params: { days: 14, use_model: true },
      timeout: 60_000,
    })
  })
})
