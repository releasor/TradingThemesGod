import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeMiningBoard } from './ThemeMiningBoard'
import type { MiningBoardResponse, MiningCardItem } from '@/types/mining'

vi.mock('@/components/AppCardNav', () => ({
  AppCardNav: () => <div data-testid="app-card-nav" />,
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: (selector: (state: { token: string | null }) => unknown) =>
    selector({ token: null }),
}))

vi.mock('@/api/mining', () => ({
  fetchMiningBoard: vi.fn(),
  fetchMiningCard: vi.fn(),
  ensureMining: vi.fn(),
  ensureMiningNote: vi.fn(),
}))

import { ensureMining, fetchMiningBoard, fetchMiningCard } from '@/api/mining'

function mockCard(overrides: Partial<MiningCardItem> = {}): MiningCardItem {
  return {
    id: 1,
    trade_date: '2026-07-25',
    theme_id: 7,
    theme_name: '人形机器人',
    mining_type: 'low_branch',
    score: 72,
    rank: 1,
    lifecycle_stage: 'fermentation',
    strength_score: 68,
    rationale: '题材偏强，成份股滞后可挖',
    score_breakdown: {},
    degraded: false,
    missing_metrics: [],
    member_count: 2,
    members: [
      {
        stock_id: 101,
        stock_code: '300024',
        stock_name: '机器人',
        concept_node_id: null,
        concept_node_name: null,
        score: 55,
        rank: 1,
        role_tag: 'laggard',
        metrics: {},
        rise_fall_pct: 1.2,
      },
    ],
    note: null,
    ...overrides,
  }
}

function mockBoard(overrides: Partial<MiningBoardResponse> = {}): MiningBoardResponse {
  return {
    trade_date: '2026-07-25',
    low_branch: [mockCard()],
    catch_up: [
      mockCard({
        id: 2,
        mining_type: 'catch_up',
        theme_name: '商业航天',
        theme_id: 8,
        rationale: '中位下正涨补涨',
        members: [],
        member_count: 0,
      }),
    ],
    hidden_leader: [
      mockCard({
        id: 3,
        mining_type: 'hidden_leader',
        theme_name: '固态电池',
        theme_id: 9,
        rationale: '非 Top2 但综合分靠前',
        members: [],
        member_count: 1,
      }),
    ],
    ...overrides,
  }
}

function renderBoard(initialEntry = '/mining?date=2026-07-25') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <ThemeMiningBoard />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ThemeMiningBoard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fetchMiningBoard).mockResolvedValue(mockBoard())
    vi.mocked(ensureMining).mockResolvedValue({
      trade_date: '2026-07-25',
      theme_count: 10,
      card_count: 3,
      counts: { low_branch: 1, catch_up: 1, hidden_leader: 1 },
    })
    vi.mocked(fetchMiningCard).mockResolvedValue(
      mockCard({
        id: 3,
        members: [
          {
            stock_id: 201,
            stock_code: '002594',
            stock_name: '比亚迪',
            concept_node_id: 1,
            concept_node_name: '固态电池',
            score: 80,
            rank: 1,
            role_tag: 'shadow_leader',
            metrics: {},
            rise_fall_pct: 3.5,
          },
        ],
      })
    )
  })

  it('renders three columns with cards', async () => {
    renderBoard()

    expect(screen.getByRole('heading', { name: '题材挖掘' })).toBeInTheDocument()

    await waitFor(() => {
      expect(fetchMiningBoard).toHaveBeenCalledWith({ trade_date: '2026-07-25' })
    })

    expect(await screen.findByTestId('mining-board-columns')).toBeInTheDocument()
    expect(screen.getByTestId('mining-column-low-branch')).toBeInTheDocument()
    expect(screen.getByTestId('mining-column-catch-up')).toBeInTheDocument()
    expect(screen.getByTestId('mining-column-hidden-leader')).toBeInTheDocument()

    expect(screen.getByRole('heading', { name: '低位分支' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '补涨' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '隐性龙头' })).toBeInTheDocument()

    expect(screen.getByText('人形机器人')).toBeInTheDocument()
    expect(screen.getByText('商业航天')).toBeInTheDocument()
    expect(screen.getByText('固态电池')).toBeInTheDocument()
    expect(screen.getByText(/题材偏强/)).toBeInTheDocument()
  })

  it('expands card members on click', async () => {
    renderBoard()
    await screen.findByText('人形机器人')

    await userEvent.click(screen.getByRole('button', { name: /展开 · 2/ }))
    expect(await screen.findByTestId('mining-card-members-1')).toBeInTheDocument()
    expect(screen.getByText('300024')).toBeInTheDocument()
    expect(screen.getByText('机器人')).toBeInTheDocument()
  })

  it('fetches card detail when expanding without preview members', async () => {
    renderBoard()
    await screen.findByText('固态电池')

    const hiddenCard = screen.getByTestId('mining-card-3')
    await userEvent.click(
      hiddenCard.querySelector('button[aria-expanded]') as HTMLButtonElement
    )

    await waitFor(() => {
      expect(fetchMiningCard).toHaveBeenCalledWith(3)
    })

    expect(await screen.findByText('002594')).toBeInTheDocument()
    expect(screen.getByText('比亚迪')).toBeInTheDocument()
  })

  it('calls ensureMining when clicking 重新挖掘', async () => {
    renderBoard()
    await screen.findByText('人形机器人')

    await userEvent.click(screen.getByRole('button', { name: '重新挖掘' }))

    await waitFor(() => {
      expect(ensureMining).toHaveBeenCalledWith({ trade_date: '2026-07-25' })
    })
  })

  it('fetches board without date param when absent', async () => {
    renderBoard('/mining')
    await waitFor(() => {
      expect(fetchMiningBoard).toHaveBeenCalledWith({})
    })
  })
})
