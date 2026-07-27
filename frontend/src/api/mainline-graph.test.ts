import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '@/api/client'

import {
  acceptMainlineGraphEdge,
  createMainlineGraphDraft,
  ensureMainlineGraph,
  fetchMainlineGraphVersions,
  fetchMainlineGraphView,
  fetchMainlineThemeConcept,
  patchMainlineGraphEdges,
  publishMainlineGraphVersion,
} from './mainline-graph'

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
}))

describe('mainline-graph api', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches view without params', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { trade_date: '2026-07-26', version: null, nodes: [], edges: [], empty: true },
    })
    await fetchMainlineGraphView()
    expect(apiClient.get).toHaveBeenCalledWith('/mainline-graph/view', { params: {} })
  })

  it('fetches view with trade_date and version_id', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { trade_date: '2026-07-25', version: null, nodes: [], edges: [], empty: true },
    })
    await fetchMainlineGraphView({ trade_date: '2026-07-25', version_id: 3 })
    expect(apiClient.get).toHaveBeenCalledWith('/mainline-graph/view', {
      params: { trade_date: '2026-07-25', version_id: 3 },
    })
  })

  it('fetches versions with trade_date', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { trade_date: '2026-07-25', items: [] },
    })
    await fetchMainlineGraphVersions({ trade_date: '2026-07-25' })
    expect(apiClient.get).toHaveBeenCalledWith('/mainline-graph/versions', {
      params: { trade_date: '2026-07-25' },
    })
  })

  it('ensures with defaults', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        trade_date: '2026-07-26',
        version_id: 1,
        node_count: 0,
        edge_count: 0,
        model_queued: false,
      },
    })
    await ensureMainlineGraph()
    expect(apiClient.post).toHaveBeenCalledWith(
      '/mainline-graph/ensure',
      { use_model: false },
      { timeout: 60_000 }
    )
  })

  it('ensures with trade_date and use_model', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        trade_date: '2026-07-24',
        version_id: 2,
        node_count: 5,
        edge_count: 3,
        model_queued: true,
      },
    })
    await ensureMainlineGraph({ trade_date: '2026-07-24', use_model: true })
    expect(apiClient.post).toHaveBeenCalledWith(
      '/mainline-graph/ensure',
      { trade_date: '2026-07-24', use_model: true },
      { timeout: 60_000 }
    )
  })

  it('creates draft', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: 9, kind: 'draft' } })
    await createMainlineGraphDraft({
      trade_date: '2026-07-25',
      source_version_id: 1,
      title: '手工草稿',
    })
    expect(apiClient.post).toHaveBeenCalledWith('/mainline-graph/versions', {
      trade_date: '2026-07-25',
      source_version_id: 1,
      title: '手工草稿',
    })
  })

  it('patches edges on draft version', async () => {
    vi.mocked(apiClient.patch).mockResolvedValue({
      data: { trade_date: '2026-07-25', version: null, nodes: [], edges: [], empty: false },
    })
    await patchMainlineGraphEdges(9, {
      edges: [{ op: 'upsert', from_theme_id: 1, to_theme_id: 2, weight: 0.4 }],
    })
    expect(apiClient.patch).toHaveBeenCalledWith('/mainline-graph/versions/9/edges', {
      edges: [{ op: 'upsert', from_theme_id: 1, to_theme_id: 2, weight: 0.4 }],
    })
  })

  it('publishes version', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: 9, status: 'published' } })
    await publishMainlineGraphVersion(9)
    expect(apiClient.post).toHaveBeenCalledWith('/mainline-graph/versions/9/publish')
  })

  it('accepts suggested edge into draft', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: 12, status: 'active' } })
    await acceptMainlineGraphEdge(12, { draft_version_id: 9 })
    expect(apiClient.post).toHaveBeenCalledWith('/mainline-graph/edges/12/accept', {
      draft_version_id: 9,
    })
  })

  it('fetches theme concept', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        theme_id: 7,
        theme_name: '人形机器人',
        concept_graph: { roots: [], node_count: 0, stock_count: 0, max_depth: 0, updated_at: null },
      },
    })
    await fetchMainlineThemeConcept(7, { trade_date: '2026-07-25' })
    expect(apiClient.get).toHaveBeenCalledWith('/mainline-graph/themes/7/concept', {
      params: { trade_date: '2026-07-25' },
    })
  })
})
