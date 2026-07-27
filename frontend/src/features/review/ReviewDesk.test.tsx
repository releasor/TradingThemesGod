import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReviewDesk } from './ReviewDesk'
import type { ReviewDayResponse } from '@/types/review'

vi.mock('@/components/AppCardNav', () => ({
  AppCardNav: () => <div data-testid="app-card-nav" />,
}))

vi.mock('@/api/review', () => ({
  fetchReviewDay: vi.fn(),
  fetchReviewTheme: vi.fn(),
  fetchReviewReport: vi.fn(),
  ensureReviewReport: vi.fn(),
  fetchReviewDays: vi.fn(),
}))

vi.mock('@/api/trading-calendar', () => ({
  resolveTradeDate: vi.fn(async (date?: string) => ({
    input_date: date ?? '2026-07-24',
    trade_date: date === '2026-07-26' ? '2026-07-24' : date ?? '2026-07-24',
  })),
  fetchCalendarStatus: vi.fn(),
  syncTradingCalendar: vi.fn(),
}))

import {
  ensureReviewReport,
  fetchReviewDay,
  fetchReviewReport,
} from '@/api/review'
import { resolveTradeDate } from '@/api/trading-calendar'

function mockDay(overrides: Partial<ReviewDayResponse> = {}): ReviewDayResponse {
  return {
    trade_date: '2026-07-24',
    degraded: true,
    missing_sources: ['review_events'],
    runs: [],
    strategy_card: {
      title: '策略卡',
      primary_strategy: '连板接力',
      secondary_strategy: '补涨',
      operation_advice: '低吸确认',
    },
    candidates: [],
    stage_transitions: [],
    performance: null,
    report_summary: null,
    ...overrides,
  }
}

function renderDesk(initialEntry = '/review?date=2026-07-24') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <ReviewDesk />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ReviewDesk', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(resolveTradeDate).mockImplementation(async (date?: string) => ({
      input_date: date ?? '2026-07-24',
      trade_date:
        date === '2026-07-26' || date === '2026-07-25'
          ? '2026-07-24'
          : (date ?? '2026-07-24'),
    }))
    vi.mocked(fetchReviewDay).mockResolvedValue(mockDay())
    vi.mocked(ensureReviewReport).mockResolvedValue({
      trade_date: '2026-07-24',
      user_id: null,
      status: 'rule_fallback',
      content_md: '规则摘要',
      content_json: {},
      model_name: null,
      error: null,
      source_run_ids: [],
    })
    vi.mocked(fetchReviewReport).mockResolvedValue({
      trade_date: '2026-07-24',
      user_id: null,
      status: 'rule_fallback',
      content_md: '规则摘要',
      content_json: {},
      model_name: null,
      error: null,
      source_run_ids: [],
    })
  })

  it('renders day mode degraded banner and strategy section', async () => {
    renderDesk()

    expect(screen.getByRole('heading', { name: '复盘台' })).toBeInTheDocument()

    await waitFor(() => {
      expect(fetchReviewDay).toHaveBeenCalledWith('2026-07-24')
    })

    expect(await screen.findByTestId('review-degraded-banner')).toBeInTheDocument()
    expect(screen.getByText(/降级投影/)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '策略卡' })).toBeInTheDocument()
    expect(screen.getByText('连板接力')).toBeInTheDocument()
  })

  it('rolls weekend date param to previous Friday', async () => {
    renderDesk('/review?date=2026-07-26')

    await waitFor(() => {
      expect(fetchReviewDay).toHaveBeenCalledWith('2026-07-24')
    })
  })
})
