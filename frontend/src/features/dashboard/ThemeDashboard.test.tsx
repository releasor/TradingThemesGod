/** 题材看板主页面测试 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { ThemeDashboard } from './ThemeDashboard'

vi.mock('@/api/theme', () => ({
  fetchThemeRanking: vi.fn(),
  fetchThemes: vi.fn(),
  fetchMarketSignals: vi.fn(),
  fetchIndicatorSignals: vi.fn(),
}))

vi.mock('@/api/scraper', () => ({
  fetchLatestSuccessfulRun: vi.fn(),
  fetchDashboardScraperSources: vi.fn(),
  runScraperAndWait: vi.fn(),
}))

vi.mock('@/api/short-term', () => ({
  fetchShortTermOverview: vi.fn(),
  fetchFirstToSecondCandidates: vi.fn(),
  refreshFirstToSecondCandidates: vi.fn(),
}))

vi.mock('@/components/NewsTimeline', () => ({
  NewsTimeline: () => (
    <section aria-labelledby="news-heading">
      <h2 id="news-heading">实时资讯</h2>
    </section>
  ),
}))

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

import {
  fetchIndicatorSignals,
  fetchMarketSignals,
  fetchThemeRanking,
  fetchThemes,
} from '@/api/theme'
import { fetchDashboardScraperSources, fetchLatestSuccessfulRun, runScraperAndWait } from '@/api/scraper'
import {
  fetchFirstToSecondCandidates,
  fetchShortTermOverview,
  refreshFirstToSecondCandidates,
} from '@/api/short-term'

vi.mock('@/components/charts/ThemeRiseFallBar', () => ({
  ThemeRiseFallBar: ({
    themes,
    onThemeClick,
  }: {
    themes: Array<{ id: number; name: string }>
    onThemeClick?: (themeId: number) => void
  }) => (
    <div data-testid="rise-fall-chart">
      {themes.length} themes
      {themes.map((theme) => (
        <button key={theme.id} type="button" onClick={() => onThemeClick?.(theme.id)}>
          {theme.name}
        </button>
      ))}
    </div>
  ),
}))

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

const mockThemes = [
  {
    id: 1,
    name: '人工智能',
    code: 'AI001',
    heat_index: 95.5,
    rise_fall_pct: 3.2,
    stock_count: 50,
    tags: ['AI', '科技'],
    category: '科技',
    description: 'AI 主题',
    source: 'eastmoney',
  },
  {
    id: 2,
    name: '新能源',
    code: 'NE002',
    heat_index: 88.0,
    rise_fall_pct: -1.5,
    stock_count: 30,
    tags: ['能源'],
    category: '能源',
    description: '新能源主题',
    source: 'eastmoney',
  },
]

const mockMarketSignals = [
  {
    id: 81,
    name: '昨日涨停',
    code: 'BK0815',
    heat_index: 75,
    rise_fall_pct: 2.5,
    stock_count: 46,
    tags: null,
    category: null,
    description: null,
    source: 'eastmoney',
  },
]

const mockIndicatorSignals = [
  {
    id: 90,
    name: '百日新高',
    code: 'BK1676',
    heat_index: 60,
    rise_fall_pct: 1.8,
    stock_count: 25,
    tags: null,
    category: null,
    description: null,
    source: 'eastmoney',
  },
]

function renderDashboard() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ThemeDashboard />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ThemeDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fetchThemeRanking).mockResolvedValue({
      items: mockThemes,
      limit: 2,
    })
    vi.mocked(fetchThemes).mockResolvedValue({
      items: mockThemes,
      total: 279,
      page: 1,
      page_size: 20,
      total_pages: 1,
    })
    vi.mocked(fetchMarketSignals).mockResolvedValue({
      items: mockMarketSignals,
      limit: mockMarketSignals.length,
    })
    vi.mocked(fetchIndicatorSignals).mockResolvedValue({
      items: mockIndicatorSignals,
      limit: mockIndicatorSignals.length,
    })
    vi.mocked(fetchDashboardScraperSources).mockResolvedValue([
      {
        id: 'eastmoney',
        label: '东方财富',
        description: '题材列表、涨跌幅、成分股与市场快照',
        dashboard_selectable: true,
        is_default: true,
      },
      {
        id: 'akshare',
        label: 'AKShare',
        description: 'A 股实时行情、涨跌幅与市值数据',
        dashboard_selectable: true,
        is_default: false,
      },
    ])
    vi.mocked(fetchLatestSuccessfulRun).mockResolvedValue({
      run_id: 9,
      source: 'eastmoney',
      status: 'completed',
      started_at: '2026-07-16T01:00:00Z',
      finished_at: '2026-07-16T01:02:03',
      items_scraped: 100,
      error_message: null,
    })
    vi.mocked(fetchShortTermOverview).mockResolvedValue({
      trade_date: '2026-07-21',
      period: 'today',
      period_label: '当日',
      start_date: '2026-07-21',
      end_date: '2026-07-21',
      degraded: false,
      missing_sources: [],
      market_emotion: '情绪开',
      short_term_outlook: '指数与情绪共振',
      operation_advice: '做连板',
      tracking_focus: ['连板梯队'],
      core_conclusion: '优先主线前排',
      risk_signals: [],
      sector_count: 3,
      candidate_count: 0,
      strategy_card: {
        title: '指数情绪策略卡',
        index_strength: 'strong',
        emotion_strength: 'strong',
        primary_strategy: '连板接力',
        secondary_strategy: '主升分歧接力',
        operation_advice: '指数强、情绪强，做连板。',
        focus_targets: ['连板梯队'],
        rationale: ['日均连板 28.0'],
      },
    })
    vi.mocked(fetchFirstToSecondCandidates).mockResolvedValue({
      trade_date: '2026-07-21',
      previous_trade_date: '2026-07-20',
      refreshed_at: '2026-07-21T10:30:00Z',
      degraded: true,
      missing_sources: ['model_catalyst'],
      candidates: [
        {
          code: '000001',
          name: '平安银行',
          theme_name: '金融科技',
          price: 12.3,
          market_cap: 120,
          float_market_cap: 60,
          turnover_rate: 8.5,
          amount: 9.2,
          first_limit_up_at: '09:42:00',
          open_board_count: 0,
          score: 86,
          decision: 'candidate',
          matched_rules: ['今日仍在涨停'],
          excluded_rules: [],
          risk_flags: ['模型催化缺失'],
          catalysts: ['行业催化：金融科技'],
          operation_advice: '只做换手晋级确认。',
          core_conclusion: '具备一进二观察价值。',
        },
      ],
      excluded_count: 0,
    })
    vi.mocked(refreshFirstToSecondCandidates).mockResolvedValue({
      trade_date: '2026-07-21',
      previous_trade_date: '2026-07-20',
      refreshed_at: '2026-07-21T10:30:00Z',
      degraded: false,
      missing_sources: [],
      candidates: [],
      excluded_count: 0,
    })
  })

  it('显示题材卡片', async () => {
    renderDashboard()
    expect(await screen.findByRole('heading', { name: '人工智能' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '新能源' })).toBeInTheDocument()
  })

  it('独立展示市场表现与真实题材总数', async () => {
    renderDashboard()
    expect(await screen.findByRole('heading', { name: '市场表现' })).toBeInTheDocument()
    expect(await screen.findByText('昨日涨停')).toBeInTheDocument()
    expect(await screen.findByText('279')).toBeInTheDocument()
  })

  it('独立展示行情指标排序列', async () => {
    renderDashboard()
    expect(await screen.findByRole('heading', { name: '行情指标' })).toBeInTheDocument()
    expect(await screen.findByText('百日新高')).toBeInTheDocument()
  })

  it('大屏下涨跌幅、行情指标与市场表现并排', async () => {
    renderDashboard()
    const rankingGrid = await screen.findByTestId('dashboard-ranking-grid')
    expect(rankingGrid).toHaveClass('lg:grid-cols-2', 'xl:grid-cols-3')
    expect(rankingGrid).toContainElement(screen.getByRole('heading', { name: '涨跌幅 Top 20' }))
    expect(rankingGrid).toContainElement(screen.getByRole('heading', { name: '行情指标' }))
    expect(rankingGrid).toContainElement(screen.getByRole('heading', { name: '市场表现' }))
  })

  it('超宽屏下资讯在右侧栏', async () => {
    renderDashboard()
    const contentGrid = await screen.findByTestId('dashboard-content-grid')
    const mainColumn = screen.getByTestId('dashboard-main-column')
    const newsSidebar = screen.getByTestId('dashboard-news-sidebar')
    expect(contentGrid).toHaveClass('xl:grid-cols-[minmax(0,2fr)_minmax(340px,1fr)]')
    expect(mainColumn).toContainElement(screen.getByRole('heading', { name: '涨跌幅 Top 20' }))
    expect(newsSidebar).toContainElement(screen.getByRole('heading', { name: '实时资讯' }))
  })

  it('热门题材与一进二参考并排', async () => {
    renderDashboard()
    const hotThemesGrid = await screen.findByTestId('dashboard-hot-themes-grid')
    expect(hotThemesGrid).toContainElement(screen.getByRole('heading', { name: /热门题材 Top/ }))
    expect(hotThemesGrid).toContainElement(screen.getByRole('heading', { name: '一进二打板参考' }))
  })

  it('点击市场表现可进入详情', async () => {
    renderDashboard()
    await userEvent.click(await screen.findByRole('button', { name: /昨日涨停/ }))
    expect(mockNavigate).toHaveBeenCalledWith('/themes/81', { state: { from: '/' } })
  })

  it('市场表现失败时不影响普通题材', async () => {
    vi.mocked(fetchMarketSignals).mockRejectedValue(new Error('Network error'))
    renderDashboard()
    expect(await screen.findByText('市场表现加载失败')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '人工智能' })).toBeInTheDocument()
  })

  it('点击刷新只重拉看板且不触发爬虫', async () => {
    const user = userEvent.setup()
    renderDashboard()

    await waitFor(() => {
      expect(fetchThemeRanking).toHaveBeenCalledTimes(1)
      expect(fetchThemes).toHaveBeenCalledTimes(2)
      expect(fetchMarketSignals).toHaveBeenCalledTimes(1)
      expect(fetchIndicatorSignals).toHaveBeenCalledTimes(1)
    })

    await user.click(screen.getByRole('button', { name: '刷新' }))

    await waitFor(() => {
      expect(fetchThemeRanking).toHaveBeenCalledTimes(2)
      expect(fetchThemes).toHaveBeenCalledTimes(4)
      expect(fetchMarketSignals).toHaveBeenCalledTimes(2)
      expect(fetchIndicatorSignals).toHaveBeenCalledTimes(2)
      expect(fetchShortTermOverview).toHaveBeenCalledTimes(2)
      expect(runScraperAndWait).not.toHaveBeenCalled()
    })
    expect(await screen.findByText('看板已刷新')).toBeInTheDocument()
  })

  it('点击全量更新时触发爬虫并刷新看板', async () => {
    const user = userEvent.setup()
    vi.mocked(runScraperAndWait).mockResolvedValue({
      run_id: 10,
      source: 'eastmoney',
      status: 'completed',
      started_at: '2026-07-16T02:00:00Z',
      finished_at: '2026-07-16T02:03:04Z',
      items_scraped: 126,
      error_message: null,
    })
    renderDashboard()
    await screen.findByText('2026-07-16 09:02:03')

    await user.click(screen.getByRole('button', { name: '全量更新' }))

    const successControls = within(screen.getByTestId('quick-stats')).getByTestId('dashboard-data-controls')
    expect(await within(successControls).findByText('东方财富全量更新成功，共更新 126 条数据')).toBeInTheDocument()
    expect(runScraperAndWait).toHaveBeenCalledWith('eastmoney')
    expect(fetchThemeRanking).toHaveBeenCalledTimes(2)
    expect(fetchMarketSignals).toHaveBeenCalledTimes(2)
    expect(fetchIndicatorSignals).toHaveBeenCalledTimes(2)
  })

  it('全量更新失败时反馈错误', async () => {
    vi.mocked(runScraperAndWait).mockResolvedValue({
      run_id: 11,
      source: 'eastmoney',
      status: 'failed',
      started_at: '2026-07-16T03:00:00Z',
      finished_at: '2026-07-16T03:00:05Z',
      items_scraped: 0,
      error_message: '数据源不可用',
    })
    const user = userEvent.setup()
    renderDashboard()

    await user.click(await screen.findByRole('button', { name: '全量更新' }))

    const failControls = within(screen.getByTestId('quick-stats')).getByTestId('dashboard-data-controls')
    expect(await within(failControls).findByText('全量更新失败：数据源不可用')).toBeInTheDocument()
    expect(fetchThemeRanking).toHaveBeenCalledTimes(1)
  })

  it('全量更新过程中显示进度文案', async () => {
    let resolveRun!: (value: {
      run_id: number
      source: string
      status: 'completed'
      started_at: string
      finished_at: string
      items_scraped: number
      error_message: null
    }) => void
    vi.mocked(runScraperAndWait).mockReturnValue(
      new Promise((resolve) => {
        resolveRun = resolve
      })
    )
    const user = userEvent.setup()
    renderDashboard()

    const controls = within(await screen.findByTestId('quick-stats')).getByTestId(
      'dashboard-data-controls'
    )
    await user.click(screen.getByRole('button', { name: '全量更新' }))
    expect(within(controls).getByText('正在通过东方财富全量更新，通常需要较长时间...')).toBeInTheDocument()

    resolveRun({
      run_id: 10,
      source: 'eastmoney',
      status: 'completed',
      started_at: '2026-07-16T02:00:00Z',
      finished_at: '2026-07-16T02:03:04Z',
      items_scraped: 126,
      error_message: null,
    })

    expect(await within(controls).findByText('东方财富全量更新成功，共更新 126 条数据')).toBeInTheDocument()
  })

  it('uses selected scraper source for full update', async () => {
    const user = userEvent.setup()
    vi.mocked(runScraperAndWait).mockResolvedValue({
      run_id: 12,
      source: 'akshare',
      status: 'completed',
      started_at: '2026-07-16T02:00:00Z',
      finished_at: '2026-07-16T02:03:04Z',
      items_scraped: 88,
      error_message: null,
    })
    renderDashboard()
    await screen.findByLabelText('全量更新数据源')

    await user.selectOptions(screen.getByLabelText('全量更新数据源'), 'akshare')
    await user.click(screen.getByRole('button', { name: '全量更新' }))

    expect(runScraperAndWait).toHaveBeenCalledWith('akshare')
    const controls = within(screen.getByTestId('quick-stats')).getByTestId('dashboard-data-controls')
    expect(await within(controls).findByText('AKShare全量更新成功，共更新 88 条数据')).toBeInTheDocument()
  })

  it('单独按涨跌幅降序获取涨幅榜', async () => {
    renderDashboard()
    await waitFor(() => {
      expect(fetchThemes).toHaveBeenCalledWith({
        page: 1,
        page_size: 20,
        sort_by: 'rise_fall_pct',
        sort_order: 'desc',
      })
    })
  })
})
