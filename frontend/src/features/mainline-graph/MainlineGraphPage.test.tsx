import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MainlineGraphPage } from './MainlineGraphPage'
import type {
  MainlineGraphVersionListResponse,
  MainlineGraphViewResponse,
} from '@/types/mainline-graph'

vi.mock('@/components/AppCardNav', () => ({
  AppCardNav: () => <div data-testid="app-card-nav" />,
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: (selector: (state: { token: string | null }) => unknown) =>
    selector({ token: null }),
}))

vi.mock('echarts-for-react/lib/core', () => ({
  default: ({ style }: { style?: React.CSSProperties }) => (
    <div data-testid="echarts-mock" style={style} />
  ),
}))

vi.mock('echarts/core', () => ({
  use: vi.fn(),
}))

vi.mock('echarts/charts', () => ({
  GraphChart: {},
}))

vi.mock('echarts/components', () => ({
  TooltipComponent: {},
  LegendComponent: {},
}))

vi.mock('echarts/renderers', () => ({
  CanvasRenderer: {},
}))

vi.mock('@/api/mainline-graph', () => ({
  fetchMainlineGraphView: vi.fn(),
  fetchMainlineGraphVersions: vi.fn(),
  ensureMainlineGraph: vi.fn(),
  createMainlineGraphDraft: vi.fn(),
  patchMainlineGraphEdges: vi.fn(),
  publishMainlineGraphVersion: vi.fn(),
  acceptMainlineGraphEdge: vi.fn(),
  fetchMainlineThemeConcept: vi.fn(),
}))

vi.mock('@/api/trading-calendar', () => ({
  resolveTradeDate: vi.fn(async (date?: string) => ({
    input_date: date ?? '2026-07-25',
    trade_date: date ?? '2026-07-25',
  })),
  fetchCalendarStatus: vi.fn(),
  syncTradingCalendar: vi.fn(),
}))

import {
  ensureMainlineGraph,
  fetchMainlineGraphVersions,
  fetchMainlineGraphView,
  fetchMainlineThemeConcept,
} from '@/api/mainline-graph'

function mockView(overrides: Partial<MainlineGraphViewResponse> = {}): MainlineGraphViewResponse {
  return {
    trade_date: '2026-07-25',
    version: {
      id: 1,
      trade_date: '2026-07-25',
      kind: 'auto',
      title: null,
      status: 'open',
      parent_version_id: null,
      created_by: null,
      published_at: null,
      meta: {},
      created_at: null,
      updated_at: null,
    },
    nodes: [
      {
        id: 10,
        theme_id: 7,
        theme_name: '人形机器人',
        mainline_score: 88,
        strength_score: 72,
        lifecycle_stage: 'fermentation',
        role: 'mainline',
        payload: null,
      },
      {
        id: 11,
        theme_id: 8,
        theme_name: '商业航天',
        mainline_score: 55,
        strength_score: 60,
        lifecycle_stage: 'germination',
        role: 'branch',
        payload: null,
      },
    ],
    edges: [
      {
        id: 100,
        from_theme_id: 7,
        to_theme_id: 8,
        weight: 0.35,
        method: 'rules',
        status: 'active',
        rationale: '成分股重叠',
        created_by: null,
      },
    ],
    empty: false,
    ...overrides,
  }
}

function mockVersions(): MainlineGraphVersionListResponse {
  return {
    trade_date: '2026-07-25',
    items: [
      {
        id: 1,
        trade_date: '2026-07-25',
        kind: 'auto',
        title: null,
        status: 'open',
        parent_version_id: null,
        created_by: null,
        published_at: null,
        meta: {},
        created_at: null,
        updated_at: null,
      },
    ],
  }
}

function renderPage(initialEntry = '/mainline-graph?date=2026-07-25') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <MainlineGraphPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('MainlineGraphPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fetchMainlineGraphView).mockResolvedValue(mockView())
    vi.mocked(fetchMainlineGraphVersions).mockResolvedValue(mockVersions())
    vi.mocked(ensureMainlineGraph).mockResolvedValue({
      trade_date: '2026-07-25',
      version_id: 1,
      node_count: 2,
      edge_count: 1,
      model_queued: false,
      generated_at: '2026-07-25T12:00:00Z',
      elapsed_ms: 1200,
    })
    vi.mocked(fetchMainlineThemeConcept).mockResolvedValue({
      theme_id: 7,
      theme_name: '人形机器人',
      trade_date: '2026-07-25',
      lifecycle_stage: 'fermentation',
      strength_score: 72,
      mainline_score: 88,
      concept_graph: {
        roots: [],
        node_count: 0,
        stock_count: 0,
        max_depth: 0,
        updated_at: null,
      },
    })
  })

  it('renders page title and mode controls', async () => {
    renderPage()

    expect(screen.getByRole('heading', { name: '主线图谱' })).toBeInTheDocument()
    expect(screen.getByTestId('mainline-mode-toggle')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '叙事模式' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '概念树模式' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '生成叙事图谱' })).toBeInTheDocument()
    expect(screen.getByLabelText('选择图谱版本')).toBeInTheDocument()

    await waitFor(() => {
      expect(fetchMainlineGraphView).toHaveBeenCalledWith({ trade_date: '2026-07-25' })
    })

    expect(await screen.findByTestId('mainline-narrative-chart')).toBeInTheDocument()
  })

  it('switches to concept mode empty state without theme', async () => {
    renderPage()
    await screen.findByTestId('mainline-narrative-chart')

    await userEvent.click(screen.getByRole('button', { name: '概念树模式' }))

    expect(await screen.findByTestId('mainline-concept-empty')).toBeInTheDocument()
    expect(screen.getByText(/请先在叙事模式选题材/)).toBeInTheDocument()
  })

  it('calls ensure when clicking 生成叙事图谱', async () => {
    renderPage()
    await screen.findByTestId('mainline-narrative-chart')

    await userEvent.click(screen.getByRole('button', { name: '生成叙事图谱' }))

    await waitFor(() => {
      expect(ensureMainlineGraph).toHaveBeenCalledWith({
        trade_date: '2026-07-25',
        use_model: false,
      })
    })

    expect(await screen.findByTestId('mainline-ensure-result')).toHaveTextContent(
      '叙事图谱生成完成'
    )
    expect(screen.getByTestId('mainline-ensure-result')).toHaveTextContent('节点 2')
    expect(screen.getByTestId('mainline-ensure-result')).toHaveTextContent('边 1')
  })

  it('clears stale versionId from URL before fetching view', async () => {
    const { fetchMainlineGraphView: fetchView } = await import('@/api/mainline-graph')
    renderPage('/mainline-graph?date=2026-07-25&versionId=99')

    await waitFor(() => {
      expect(fetchView).toHaveBeenCalledWith({ trade_date: '2026-07-25' })
    })
    expect(fetchView).not.toHaveBeenCalledWith(
      expect.objectContaining({ version_id: 99 })
    )
    expect(await screen.findByTestId('mainline-narrative-chart')).toBeInTheDocument()
  })
})
