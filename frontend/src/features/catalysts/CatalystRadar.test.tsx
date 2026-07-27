import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CatalystRadar } from './CatalystRadar'
import type { CatalystFeedItem, CatalystFeedResponse } from '@/types/catalyst'

vi.mock('@/components/AppCardNav', () => ({
  AppCardNav: () => <div data-testid="app-card-nav" />,
}))

vi.mock('@/api/catalysts', () => ({
  fetchCatalystFeed: vi.fn(),
  fetchCatalystThemeSummary: vi.fn(),
  ensureCatalystClassify: vi.fn(),
}))

import {
  ensureCatalystClassify,
  fetchCatalystFeed,
  fetchCatalystThemeSummary,
} from '@/api/catalysts'

function mockItem(overrides: Partial<CatalystFeedItem> = {}): CatalystFeedItem {
  return {
    event_id: 101,
    theme_id: 7,
    theme_name: '人形机器人',
    title: '工信部推动机器人产业政策落地',
    summary: '政策加码产业链',
    source: '新华社',
    url: 'https://example.com/a',
    published_at: '2026-07-26T08:00:00Z',
    relevance_score: 88,
    freshness: 'new',
    actor_type: 'policy',
    classified_by: 'rules',
    ...overrides,
  }
}

function mockFeed(items: CatalystFeedItem[] = [mockItem()]): CatalystFeedResponse {
  return { items, total: items.length }
}

function renderRadar(initialEntry = '/catalysts') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <CatalystRadar />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('CatalystRadar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fetchCatalystFeed).mockResolvedValue(mockFeed())
    vi.mocked(fetchCatalystThemeSummary).mockResolvedValue({
      theme_id: 7,
      theme_name: '人形机器人',
      lifecycle_stage: 'fermentation',
      strength_score: 72,
      counts: { new: 2, replay: 1, policy: 2, company: 1, other: 0 },
      recent_events: [mockItem()],
      news_headlines: [],
    })
    vi.mocked(ensureCatalystClassify).mockResolvedValue({
      classified_rules: 0,
      model_queued: false,
    })
  })

  it('renders feed item with badges', async () => {
    renderRadar()

    expect(screen.getByRole('heading', { name: '催化雷达' })).toBeInTheDocument()

    await waitFor(() => {
      expect(fetchCatalystFeed).toHaveBeenCalled()
    })

    expect(await screen.findByText('工信部推动机器人产业政策落地')).toBeInTheDocument()
    const feedList = screen.getByTestId('catalyst-feed-list')
    expect(feedList).toHaveTextContent('新催化')
    expect(feedList).toHaveTextContent('政策')
    expect(feedList).toHaveTextContent('人形机器人')

    await waitFor(() => {
      expect(ensureCatalystClassify).toHaveBeenCalledWith({ use_model: false })
    })
  })

  it('renders empty feed state', async () => {
    vi.mocked(fetchCatalystFeed).mockResolvedValue({ items: [], total: 0 })
    renderRadar()

    expect(await screen.findByTestId('catalyst-feed-empty')).toBeInTheDocument()
    expect(screen.getByText(/暂无催化事件/)).toBeInTheDocument()
  })

  it('loads theme summary when themeId is in search params', async () => {
    renderRadar('/catalysts?themeId=7&freshness=new&actor=policy')

    await waitFor(() => {
      expect(fetchCatalystFeed).toHaveBeenCalledWith({
        freshness: 'new',
        actor_type: 'policy',
        theme_id: 7,
      })
    })

    await waitFor(() => {
      expect(fetchCatalystThemeSummary).toHaveBeenCalledWith(7)
    })

    expect(await screen.findByTestId('catalyst-theme-summary')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '打开题材详情' })).toHaveAttribute(
      'href',
      '/themes/7'
    )
  })
})
