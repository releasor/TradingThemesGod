/** 题材看板主页面测试 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import dayjs from 'dayjs'
import { ThemeDashboard } from './ThemeDashboard'

vi.mock('@/api/theme', () => ({
  fetchThemeRanking: vi.fn(),
  fetchThemes: vi.fn(),
  fetchMarketSignals: vi.fn(),
  fetchIndicatorSignals: vi.fn(),
}))

vi.mock('@/api/stats', () => ({
  fetchSystemStats: vi.fn(),
}))

vi.mock('@/api/scraper', () => ({
  fetchLatestSuccessfulRun: vi.fn(),
  fetchDashboardScraperSources: vi.fn(),
  refreshThemeQuotes: vi.fn(),
  runScraperWithFallback: vi.fn(),
  runScraperAndWait: vi.fn(),
}))

vi.mock('@/api/news', () => ({
  refreshNews: vi.fn(),
}))

vi.mock('@/api/short-term', () => ({
  fetchShortTermOverview: vi.fn(),
  fetchFirstToSecondCandidates: vi.fn(),
  refreshFirstToSecondCandidates: vi.fn(),
  refreshShortTermData: vi.fn(),
  refreshShortTermSignals: vi.fn(),
  fetchShortTermSectors: vi.fn(),
}))

vi.mock('@/components/AppCardNav', () => ({
  AppCardNav: () => <div data-testid="app-card-nav" />,
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
import { fetchSystemStats } from '@/api/stats'
import { refreshNews } from '@/api/news'
import {
  fetchDashboardScraperSources,
  fetchLatestSuccessfulRun,
  refreshThemeQuotes,
  runScraperWithFallback,
} from '@/api/scraper'
import {
  fetchFirstToSecondCandidates,
  fetchShortTermOverview,
  fetchShortTermSectors,
  refreshFirstToSecondCandidates,
  refreshShortTermData,
  refreshShortTermSignals,
} from '@/api/short-term'
import { useAuthStore } from '@/stores/auth'

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
    useAuthStore.getState().clearAuth()
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
    vi.mocked(fetchSystemStats).mockResolvedValue({
      themes: { total: 279, categories: [] },
      stocks: { total: 5620 },
      events: { total: 0 },
      chains: { total: 0 },
      scraper: { last_run: null },
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
    vi.mocked(refreshThemeQuotes).mockResolvedValue({
      trade_date: '2026-07-24',
      themes_updated: 495,
      refreshed_at: '2026-07-24T03:30:00Z',
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
    vi.mocked(refreshShortTermData).mockResolvedValue({
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
        title: '指数情绪策略卡 · 当日',
        index_strength: 'strong',
        emotion_strength: 'strong',
        primary_strategy: '连板接力',
        secondary_strategy: '主升分歧接力',
        operation_advice: '指数强、情绪强，做连板。',
        focus_targets: ['连板梯队'],
        rationale: ['指数强度 0.80'],
      },
      refresh_meta: {
        elapsed_ms: 1200,
        quote_source: 'eastmoney',
        quote_attempts: ['eastmoney'],
        quote_message: '',
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
    vi.mocked(fetchShortTermSectors).mockResolvedValue({
      trade_date: '2026-07-24',
      items: [],
      degraded: false,
      missing_sources: [],
    })
    vi.mocked(refreshShortTermSignals).mockResolvedValue({
      trade_date: '2026-07-24',
      status: 'success',
      signal_count: 107,
      dragon_tiger_count: 84,
      sector_count: 173,
      candidate_count: 0,
      degraded: false,
      missing_sources: [],
      source_status: {},
      error_message: null,
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

  it('策略卡随顶部刷新更新，无实时/数据库切换', async () => {
    const user = userEvent.setup()
    renderDashboard()

    expect(await screen.findByText('连板接力')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '实时' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '数据库' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '数据库分析' })).not.toBeInTheDocument()
    expect(refreshShortTermData).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: '刷新' }))

    await waitFor(() => {
      expect(refreshThemeQuotes).toHaveBeenCalledTimes(1)
      expect(refreshShortTermData).toHaveBeenCalledWith(
        { period: 'today' },
        expect.any(AbortSignal)
      )
    })
    expect(await screen.findByText(/策略卡实时数据已更新/)).toBeInTheDocument()
  })

  it('进入页面不会自动快刷，且无自动刷新控件', async () => {
    renderDashboard()

    expect(await screen.findByRole('heading', { name: '人工智能' })).toBeInTheDocument()
    expect(refreshThemeQuotes).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: '自动刷新' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '刷新' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '全量更新' })).toBeInTheDocument()
  })

  it('手动刷新后显示行情更新时间', async () => {
    const user = userEvent.setup()
    const expectedTime = dayjs('2026-07-24T03:30:00Z').format('YYYY-MM-DD HH:mm:ss')
    renderDashboard()

    await user.click(screen.getByRole('button', { name: '刷新' }))

    const stats = await screen.findByTestId('quick-stats')
    expect(await within(stats).findByText(expectedTime)).toBeInTheDocument()
    expect(await screen.findByText(new RegExp(`更新于 ${expectedTime}`))).toBeInTheDocument()
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
    expect(rankingGrid).toContainElement(
      within(rankingGrid).getByRole('heading', { name: '行情指标' })
    )
    expect(rankingGrid).toContainElement(
      within(rankingGrid).getByRole('heading', { name: '市场表现' })
    )
  })

  it('顶部统计使用股票库去重总数而非热门榜加总', async () => {
    renderDashboard()
    const stats = await screen.findByTestId('quick-stats')
    expect(within(stats).getByText('股票总数')).toBeInTheDocument()
    expect(await within(stats).findByText('5620')).toBeInTheDocument()
    expect(within(stats).queryByText('80')).not.toBeInTheDocument()
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

  it('点击刷新快刷题材行情并分板块提交，不触发全量爬虫与资讯刷新', async () => {
    const user = userEvent.setup()
    useAuthStore.getState().setAuth('test-token', {
      id: 1,
      username: 'tester',
      created_at: '2026-07-01T00:00:00Z',
    })
    renderDashboard()

    await waitFor(() => {
      expect(fetchThemeRanking).toHaveBeenCalledTimes(1)
      expect(fetchThemes).toHaveBeenCalledTimes(2)
      expect(fetchMarketSignals).toHaveBeenCalledTimes(1)
      expect(fetchIndicatorSignals).toHaveBeenCalledTimes(1)
    })
    expect(refreshThemeQuotes).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: '刷新' }))

    await waitFor(() => {
      expect(refreshThemeQuotes).toHaveBeenCalledTimes(1)
      expect(refreshShortTermSignals).toHaveBeenCalled()
      expect(refreshFirstToSecondCandidates).toHaveBeenCalled()
      expect(fetchThemeRanking.mock.calls.length).toBeGreaterThan(1)
      expect(fetchThemes.mock.calls.length).toBeGreaterThan(2)
      expect(runScraperWithFallback).not.toHaveBeenCalled()
    })
    expect(refreshNews).not.toHaveBeenCalled()
    const controls = within(screen.getByTestId('quick-stats')).getByTestId('dashboard-data-controls')
    expect(
      await within(controls).findByText(
        /已更新：题材行情 495 个；热度榜；涨幅榜；市场表现；行情指标；策略卡；短线信号.*一进二。更新于 \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}，耗时 \d+ 秒/
      )
    ).toBeInTheDocument()
  })

  it('忙碌时可取消，已提交板块保留且未完成不覆盖', async () => {
    const user = userEvent.setup()
    let resolveQuotes!: (value: {
      trade_date: string
      themes_updated: number
      refreshed_at: string
    }) => void
    const rankingBeforeRefresh = {
      items: mockThemes,
      limit: 2,
    }
    vi.mocked(refreshThemeQuotes).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveQuotes = resolve
        })
    )
    const lateRanking = {
      items: [
        {
          ...mockThemes[0],
          name: '不应覆盖的新题材',
          heat_index: 99,
        },
      ],
      limit: 1,
    }
    vi.mocked(fetchThemeRanking).mockResolvedValue(rankingBeforeRefresh)

    renderDashboard()
    expect(await screen.findByRole('heading', { name: '人工智能' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '刷新' }))
    expect(await screen.findByRole('button', { name: '取消' })).toBeInTheDocument()

    vi.mocked(fetchThemeRanking).mockResolvedValue(lateRanking)
    await user.click(screen.getByRole('button', { name: '取消' }))

    expect(await screen.findByText('已取消，已保留成功板块')).toBeInTheDocument()
    resolveQuotes({
      trade_date: '2026-07-24',
      themes_updated: 495,
      refreshed_at: '2026-07-24T03:30:00Z',
    })

    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: '不应覆盖的新题材' })).not.toBeInTheDocument()
    })
    expect(screen.getByRole('heading', { name: '人工智能' })).toBeInTheDocument()
    expect(refreshNews).not.toHaveBeenCalled()
  })

  it('点击全量更新时触发爬虫并刷新看板', async () => {
    const user = userEvent.setup()
    vi.mocked(runScraperWithFallback).mockResolvedValue({
      run_id: 10,
      source: 'eastmoney',
      status: 'completed',
      started_at: '2026-07-16T02:00:00Z',
      finished_at: '2026-07-16T02:03:04Z',
      items_scraped: 126,
      error_message: null,
      attempted_sources: ['eastmoney'],
    })
    renderDashboard()
    await screen.findByText('2026-07-16 09:02:03')
    const rankingCallsBeforeUpdate = vi.mocked(fetchThemeRanking).mock.calls.length

    await user.click(screen.getByRole('button', { name: '全量更新' }))

    const successControls = within(screen.getByTestId('quick-stats')).getByTestId(
      'dashboard-data-controls'
    )
    expect(
      await within(successControls).findByText(/东方财富全量更新成功，共更新 126 条数据/)
    ).toBeInTheDocument()
    expect(runScraperWithFallback).toHaveBeenCalledWith(
      ['eastmoney', 'akshare'],
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    )
    expect(vi.mocked(fetchThemeRanking).mock.calls.length).toBeGreaterThan(rankingCallsBeforeUpdate)
    expect(vi.mocked(fetchMarketSignals).mock.calls.length).toBeGreaterThan(1)
    expect(vi.mocked(fetchIndicatorSignals).mock.calls.length).toBeGreaterThan(1)
    expect(refreshNews).not.toHaveBeenCalled()
  })

  it('全量更新失败时反馈错误', async () => {
    vi.mocked(runScraperWithFallback).mockRejectedValue(new Error('数据源不可用'))
    const user = userEvent.setup()
    renderDashboard()
    await screen.findByRole('heading', { name: '人工智能' })
    const rankingCallsBeforeUpdate = vi.mocked(fetchThemeRanking).mock.calls.length

    await user.click(await screen.findByRole('button', { name: '全量更新' }))

    const failControls = within(screen.getByTestId('quick-stats')).getByTestId(
      'dashboard-data-controls'
    )
    expect(await within(failControls).findByText('全量更新失败：数据源不可用')).toBeInTheDocument()
    expect(vi.mocked(fetchThemeRanking).mock.calls.length).toBe(rankingCallsBeforeUpdate)
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
      attempted_sources: string[]
    }) => void
    vi.mocked(runScraperWithFallback).mockReturnValue(
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
    expect(within(controls).getByText(/正在全量更新/)).toBeInTheDocument()
    expect(within(controls).getByRole('button', { name: '取消' })).toBeInTheDocument()

    resolveRun({
      run_id: 10,
      source: 'eastmoney',
      status: 'completed',
      started_at: '2026-07-16T02:00:00Z',
      finished_at: '2026-07-16T02:03:04Z',
      items_scraped: 126,
      error_message: null,
      attempted_sources: ['eastmoney', 'akshare'],
    })

    expect(
      await within(controls).findByText(/东方财富全量更新成功，共更新 126 条数据/)
    ).toBeInTheDocument()
  })

  it('无数据源下拉，全量固定多源顺序', async () => {
    const user = userEvent.setup()
    vi.mocked(runScraperWithFallback).mockResolvedValue({
      run_id: 12,
      source: 'akshare',
      status: 'completed',
      started_at: '2026-07-16T02:00:00Z',
      finished_at: '2026-07-16T02:03:04Z',
      items_scraped: 88,
      error_message: null,
      attempted_sources: ['eastmoney', 'akshare'],
    })
    renderDashboard()
    expect(screen.queryByLabelText('全量更新数据源')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '全量更新' }))

    expect(runScraperWithFallback).toHaveBeenCalledWith(
      ['eastmoney', 'akshare'],
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    )
    const controls = within(screen.getByTestId('quick-stats')).getByTestId('dashboard-data-controls')
    expect(
      await within(controls).findByText(/AKShare全量更新成功，共更新 88 条数据/)
    ).toBeInTheDocument()
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

  it('自定义日期切换加载中仍保留策略卡', async () => {
    const user = userEvent.setup()
    let resolveCustom!: (value: Awaited<ReturnType<typeof refreshShortTermData>>) => void
    vi.mocked(refreshShortTermData).mockImplementation(async (params) => {
      if (params?.period === 'custom') {
        return new Promise((resolve) => {
          resolveCustom = resolve
        })
      }
      return {
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
        refresh_meta: {
          elapsed_ms: 900,
          quote_source: 'eastmoney',
          quote_attempts: ['eastmoney'],
          quote_message: '',
        },
      }
    })

    renderDashboard()
    expect(await screen.findByText('连板接力')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '自定义' }))
    expect(await screen.findByLabelText('自定义开始日期')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('自定义开始日期'), {
      target: { value: '2026-06-01' },
    })
    fireEvent.change(screen.getByLabelText('自定义结束日期'), {
      target: { value: '2026-06-30' },
    })

    expect(screen.getByText('指数情绪策略卡')).toBeInTheDocument()
    expect(screen.getByLabelText('自定义开始日期')).toHaveValue('2026-06-01')
    expect(screen.getByLabelText('自定义结束日期')).toHaveValue('2026-06-30')
    expect(screen.getByText('连板接力')).toBeInTheDocument()
    expect(refreshShortTermData).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: '刷新' }))

    await waitFor(() => {
      expect(refreshShortTermData).toHaveBeenCalledWith(
        {
          period: 'custom',
          startDate: '2026-06-01',
          endDate: '2026-06-30',
        },
        expect.any(AbortSignal)
      )
    })
    expect(screen.getByText('连板接力')).toBeInTheDocument()

    resolveCustom({
      trade_date: '2026-06-30',
      period: 'custom',
      period_label: '自定义',
      start_date: '2026-06-01',
      end_date: '2026-06-30',
      degraded: true,
      missing_sources: ['指数周期快照'],
      market_emotion: '情绪弱',
      short_term_outlook: '观望',
      operation_advice: '轻仓',
      tracking_focus: ['防守'],
      core_conclusion: '等待确认',
      risk_signals: [],
      sector_count: 1,
      candidate_count: 0,
      strategy_card: {
        title: '指数情绪策略卡 · 自定义',
        index_strength: 'weak',
        emotion_strength: 'weak',
        primary_strategy: '轻仓或优化持仓',
        secondary_strategy: '等待低吸反抽',
        operation_advice: '自定义区间指数弱。',
        focus_targets: ['防守'],
        rationale: ['指数强度 -0.36'],
      },
      refresh_meta: {
        elapsed_ms: 1100,
        quote_source: 'eastmoney',
        quote_attempts: ['eastmoney'],
        quote_message: '',
      },
    })

    expect(await screen.findByText('轻仓或优化持仓')).toBeInTheDocument()
  })

  it('策略加载失败后不会一直停在加载中', async () => {
    const user = userEvent.setup()
    vi.mocked(refreshShortTermData).mockImplementation(async (params) => {
      if (params?.period === 'current_week') {
        throw new Error('周期快照不可用')
      }
      return {
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
        refresh_meta: {
          elapsed_ms: 800,
          quote_source: 'eastmoney',
          quote_attempts: ['eastmoney'],
          quote_message: '',
        },
      }
    })

    renderDashboard()
    expect(await screen.findByText('连板接力')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '本周' }))
    expect(refreshShortTermData).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: '刷新' }))

    await waitFor(() => {
      expect(refreshShortTermData).toHaveBeenCalledWith(
        { period: 'current_week' },
        expect.any(AbortSignal)
      )
    })
    expect(await screen.findByText(/实时行情刷新失败/)).toBeInTheDocument()
    expect(screen.queryByText(/正在拉取实时行情/)).not.toBeInTheDocument()
    expect(screen.getByText('连板接力')).toBeInTheDocument()
  })
})
