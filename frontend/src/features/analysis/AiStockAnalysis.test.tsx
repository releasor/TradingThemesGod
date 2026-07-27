import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AiStockAnalysis } from './AiStockAnalysis'
import type { StockAiReport } from '@/types/stock-ai-report'

const authState = vi.hoisted(() => ({ token: null as string | null }))

vi.mock('@/components/AppCardNav', () => ({
  AppCardNav: () => <div data-testid="app-card-nav" />,
}))

vi.mock('@/api/short-term', () => ({
  analyzeShortTermFromDatabase: vi.fn(),
}))

vi.mock('@/api/theme', () => ({
  fetchThemeRanking: vi.fn(),
  fetchThemes: vi.fn(),
}))

vi.mock('@/api/news', () => ({
  fetchNews: vi.fn(),
}))

vi.mock('@/api/stock', () => ({
  fetchStockDetail: vi.fn(),
}))

vi.mock('@/api/stock-ai-report', () => ({
  fetchStockAiReport: vi.fn(),
  generateStockAiReport: vi.fn(),
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: (selector: (state: { token: string | null }) => unknown) =>
    selector({ token: authState.token }),
}))

import { analyzeShortTermFromDatabase } from '@/api/short-term'
import { fetchThemeRanking, fetchThemes } from '@/api/theme'
import { fetchNews } from '@/api/news'
import { fetchStockDetail } from '@/api/stock'
import { fetchStockAiReport, generateStockAiReport } from '@/api/stock-ai-report'

function mockReport(overrides: Partial<StockAiReport> = {}): StockAiReport {
  return {
    code: '600519',
    stock_name: '贵州茅台',
    verdict: 'watch',
    horizon: {
      short: { fit: 'suitable', note: '短线可观察' },
      swing: { fit: 'neutral', note: '波段中性' },
      medium_long: { fit: 'unsuitable', note: '中长线谨慎' },
    },
    confidence: 66,
    summary: '短期可观察，不宜追高。',
    sections: {
      trend: '趋势中性',
      emotion_rotation: '情绪偏强',
      themes_catalysts: '催化有限',
      stock_position: '涨幅一般',
      scenarios_actions: '等确认',
      risks: '追高风险',
    },
    full_report: '完整报告正文。供参考，非投资建议。',
    model_name: 'demo-model',
    generated_at: '2026-07-24T10:00:00Z',
    elapsed_ms: 1200,
    disclaimer: '本报告由模型根据系统聚合数据生成，仅供参考，不构成投资建议。',
    ...overrides,
  }
}

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <AiStockAnalysis />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('AiStockAnalysis', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    authState.token = null
    vi.mocked(analyzeShortTermFromDatabase).mockResolvedValue({
      trade_date: '2026-07-24',
      period: 'today',
      period_label: '当日',
      start_date: '2026-07-24',
      end_date: '2026-07-24',
      degraded: false,
      missing_sources: [],
      market_emotion: '情绪强',
      short_term_outlook: '关注主线接力',
      operation_advice: '低吸确认',
      tracking_focus: ['人工智能'],
      core_conclusion: '进攻主线',
      risk_signals: [],
      sector_count: 8,
      candidate_count: 0,
      strategy_card: {
        title: '策略卡',
        index_strength: 'strong',
        emotion_strength: 'strong',
        primary_strategy: '连板接力',
        secondary_strategy: '补涨',
        operation_advice: '强者恒强',
        focus_targets: ['算力'],
        rationale: ['指数偏强'],
      },
    })
    vi.mocked(fetchThemeRanking).mockResolvedValue({
      items: [
        {
          id: 1,
          name: '人工智能',
          code: 'AI',
          description: null,
          heat_index: 88,
          rise_fall_pct: 2.1,
          stock_count: 40,
          category: '科技',
          tags: [],
          source: null,
        },
      ],
      limit: 12,
    })
    vi.mocked(fetchThemes).mockResolvedValue({
      items: [
        {
          id: 2,
          name: '机器人',
          code: 'ROBOT',
          description: null,
          heat_index: 70,
          rise_fall_pct: 4.4,
          stock_count: 20,
          category: '科技',
          tags: [],
          source: null,
        },
      ],
      total: 1,
      page: 1,
      page_size: 12,
      total_pages: 1,
    })
    vi.mocked(fetchNews).mockResolvedValue({
      items: [
        {
          id: 1,
          source: 'demo',
          category: '市场',
          title: '政策催化算力',
          summary: null,
          url: 'https://example.com',
          published_at: '2026-07-24T09:00:00Z',
          crawled_at: '2026-07-24T09:01:00Z',
          heat_score: 70,
        },
      ],
      total: 1,
    })
    vi.mocked(fetchStockDetail).mockResolvedValue({
      id: 1,
      code: '600519',
      name: '贵州茅台',
      industry: '白酒',
      market_cap: 1,
      current_price: 1600,
      rise_fall_pct: 1.5,
      exchange: 'SH',
      created_at: '',
      updated_at: '',
      recent_events: [],
    })
  })

  it('shows market context on the left by default', async () => {
    renderPage()

    expect(await screen.findByRole('heading', { name: 'AI 个股分析' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: '市场上下文' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'AI 研判' })).toBeInTheDocument()
    expect(await screen.findByText('近期趋势')).toBeInTheDocument()
    expect(screen.getByText('市场情绪')).toBeInTheDocument()
    expect(screen.getByText(/规则汇总结论/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '登录' })).toBeInTheDocument()
    await waitFor(() => {
      expect(analyzeShortTermFromDatabase).toHaveBeenCalledWith(
        { period: 'today' },
        { timeout: 15_000 }
      )
    })
  })

  it('requires login before generating', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.type(await screen.findByLabelText('股票代码'), '600519')
    await user.click(screen.getByRole('button', { name: '生成 AI 研判' }))

    expect(await screen.findByText('请先登录后再生成 AI 研判。')).toBeInTheDocument()
    expect(generateStockAiReport).not.toHaveBeenCalled()
  })

  it('shows validation when stock code is incomplete', async () => {
    authState.token = 'token'
    const user = userEvent.setup()
    renderPage()
    await user.type(await screen.findByLabelText('股票代码'), '6005')
    await user.click(screen.getByRole('button', { name: '生成 AI 研判' }))

    expect(await screen.findByText('请输入 6 位股票代码后再生成研判。')).toBeInTheDocument()
    expect(generateStockAiReport).not.toHaveBeenCalled()
  })

  it('loads cached report into the right panel', async () => {
    authState.token = 'token'
    vi.mocked(fetchStockAiReport).mockResolvedValue(mockReport())

    const user = userEvent.setup()
    renderPage()
    await user.type(await screen.findByLabelText('股票代码'), '600519')
    await user.click(screen.getByRole('button', { name: '生成 AI 研判' }))

    expect(await screen.findByText('AI 研判结论')).toBeInTheDocument()
    expect(screen.getByText('观望')).toBeInTheDocument()
    expect(screen.getByText(/短期可观察，不宜追高/)).toBeInTheDocument()
    expect(screen.getByText(/完整报告正文/)).toBeInTheDocument()
    expect(generateStockAiReport).not.toHaveBeenCalled()
    expect(fetchStockDetail).toHaveBeenCalledWith('600519')
  })

  it('generates report when cache misses', async () => {
    authState.token = 'token'
    vi.mocked(fetchStockAiReport).mockRejectedValue({
      response: { status: 404, data: { detail: '尚未生成' } },
    })
    vi.mocked(generateStockAiReport).mockResolvedValue(
      mockReport({ verdict: 'buy', summary: '可关注买入' })
    )

    const user = userEvent.setup()
    renderPage()
    await user.type(await screen.findByLabelText('股票代码'), '600519')
    await user.click(screen.getByRole('button', { name: '生成 AI 研判' }))

    await waitFor(() => {
      expect(generateStockAiReport).toHaveBeenCalledWith('600519', { force: false })
    })
    expect(await screen.findByText('买入')).toBeInTheDocument()
    expect(screen.getByText('可关注买入')).toBeInTheDocument()
  })

  it('shows model setup hint on 409', async () => {
    authState.token = 'token'
    vi.mocked(fetchStockAiReport).mockRejectedValue({
      response: { status: 404 },
    })
    vi.mocked(generateStockAiReport).mockRejectedValue({
      response: {
        status: 409,
        data: { detail: '请先在模型设置中配置并启用默认模型' },
      },
    })

    const user = userEvent.setup()
    renderPage()
    await user.type(await screen.findByLabelText('股票代码'), '600519')
    await user.click(screen.getByRole('button', { name: '生成 AI 研判' }))

    expect(
      await screen.findByText(/请先在模型设置中配置并启用默认模型/)
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '前往模型设置' })).toHaveAttribute(
      'href',
      '/settings/models'
    )
  })

  it('regenerates with force=true when report already shown', async () => {
    authState.token = 'token'
    vi.mocked(fetchStockAiReport).mockResolvedValue(mockReport())
    vi.mocked(generateStockAiReport).mockResolvedValue(
      mockReport({ summary: '重新生成后的结论' })
    )

    const user = userEvent.setup()
    renderPage()
    await user.type(await screen.findByLabelText('股票代码'), '600519')
    await user.click(screen.getByRole('button', { name: '生成 AI 研判' }))
    expect(await screen.findByText('AI 研判结论')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '重新生成 AI 研判' }))
    await waitFor(() => {
      expect(generateStockAiReport).toHaveBeenCalledWith('600519', { force: true })
    })
    expect(await screen.findByText('重新生成后的结论')).toBeInTheDocument()
  })
})
