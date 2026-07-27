import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '@/api/client'

import {
  ensureMining,
  ensureMiningNote,
  fetchMiningBoard,
  fetchMiningCard,
} from './mining'

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

describe('mining api', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches board without params', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { trade_date: '2026-07-25', low_branch: [], catch_up: [], hidden_leader: [] },
    })
    await fetchMiningBoard()
    expect(apiClient.get).toHaveBeenCalledWith('/mining/board', { params: {} })
  })

  it('fetches board with trade_date', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { trade_date: '2026-07-24', low_branch: [], catch_up: [], hidden_leader: [] },
    })
    await fetchMiningBoard({ trade_date: '2026-07-24' })
    expect(apiClient.get).toHaveBeenCalledWith('/mining/board', {
      params: { trade_date: '2026-07-24' },
    })
  })

  it('fetches card by id', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { id: 9 } })
    await fetchMiningCard(9)
    expect(apiClient.get).toHaveBeenCalledWith('/mining/cards/9')
  })

  it('ensures mining without date', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { trade_date: '2026-07-25', theme_count: 0, card_count: 0, counts: {} },
    })
    await ensureMining()
    expect(apiClient.post).toHaveBeenCalledWith('/mining/ensure', null, {
      params: {},
      timeout: 60_000,
    })
  })

  it('ensures mining with trade_date', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { trade_date: '2026-07-24', theme_count: 3, card_count: 5, counts: {} },
    })
    await ensureMining({ trade_date: '2026-07-24' })
    expect(apiClient.post).toHaveBeenCalledWith('/mining/ensure', null, {
      params: { trade_date: '2026-07-24' },
      timeout: 60_000,
    })
  })

  it('ensures mining note with 60s timeout', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { id: 1, card_id: 9, user_id: 2, status: 'pending', content_md: '' },
    })
    await ensureMiningNote(9)
    expect(apiClient.post).toHaveBeenCalledWith('/mining/cards/9/note/ensure', null, {
      timeout: 60_000,
    })
  })
})
