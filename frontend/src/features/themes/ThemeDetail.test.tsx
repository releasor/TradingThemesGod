/** ThemeDetail 题材详情页测试 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeDetail } from './ThemeDetail'
import type { ThemeDetailResponse } from '@/types/theme'

// --- Mocks ---

const mockNavigate = vi.fn()
let mockLocationState: { from?: string } | null = null

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ id: '1' }),
    useLocation: () => ({ state: mockLocationState }),
  }
})

it('places recent driver events in the right rail on the detail page', async () => {
  vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeWithInsights)
  renderThemeDetail()

  const contentGrid = await screen.findByTestId('theme-detail-content-grid')
  const sideRail = screen.getByTestId('theme-detail-side-rail')
  const eventHeading = screen.getByRole('heading', { name: '最近驱动事件' })

  expect(contentGrid).toHaveClass('xl:grid-cols-[minmax(0,1fr)_360px]')
  expect(sideRail).toContainElement(eventHeading)
})

vi.mock('@/api/theme', () => ({
  fetchThemeDetail: vi.fn(),
  refreshConceptGraph: vi.fn(),
  refreshThemeInsights: vi.fn(),
}))

vi.mock('@/components/IndustryChainSection', () => ({
  IndustryChainSection: ({ chains: _chains, themeId }: { chains: unknown; themeId: number }) => (
    <div data-testid="industry-chain-section" data-theme-id={themeId}>
      IndustryChainSection
    </div>
  ),
}))

vi.mock('@/components/ThemeConstituentStocks', () => ({
  ThemeConstituentStocks: ({ themeId }: { themeId: number }) => (
    <div data-testid="theme-constituent-stocks" data-theme-id={themeId}>
      ThemeConstituentStocks
    </div>
  ),
}))

vi.mock('@/components/charts/ThemeHeatTrendLine', () => ({
  ThemeHeatTrendLine: ({ data }: { data: unknown[] }) => (
    <div data-testid="heat-trend-line" data-points={data.length}>
      ThemeHeatTrendLine
    </div>
  ),
}))

vi.mock('@/components/charts/IndustryChainPie', () => ({
  IndustryChainPie: ({ chains: _chains }: { chains: unknown }) => (
    <div data-testid="industry-chain-pie">IndustryChainPie</div>
  ),
}))

// --- Imports after mocks ---

import { fetchThemeDetail, refreshConceptGraph, refreshThemeInsights } from '@/api/theme'

// --- Fixtures ---

const mockThemeDetail: ThemeDetailResponse = {
  id: 1,
  name: '人工智能',
  code: 'AI',
  description: 'AI 相关题材，涵盖大模型、自动驾驶等方向',
  heat_index: 95.5,
  rise_fall_pct: 2.35,
  stock_count: 50,
  category: '科技',
  tags: ['AI', '机器学习', '大模型'],
  source: '东方财富',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-15T00:00:00Z',
  industry_chains: {
    upstream: [
      {
        id: 1,
        level: 'upstream',
        name: '芯片设计',
        description: '上游芯片',
        representative_companies: ['华为海思'],
        sort_order: 1,
      },
    ],
    midstream: [
      {
        id: 2,
        level: 'midstream',
        name: '模型训练',
        description: '中游模型',
        representative_companies: ['百度'],
        sort_order: 1,
      },
    ],
    downstream: [
      {
        id: 3,
        level: 'downstream',
        name: '智能终端',
        description: '下游应用',
        representative_companies: ['小米'],
        sort_order: 1,
      },
    ],
  },
  chain_stock_counts: {
    upstream: 8,
    midstream: 5,
    downstream: 3,
  },
  concept_graph: {
    roots: [],
    node_count: 0,
    stock_count: 0,
    max_depth: 0,
    updated_at: null,
  },
  profile: null,
  recent_driver_events: [],
  market_snapshot: null,
}

const mockThemeNoTags: ThemeDetailResponse = {
  ...mockThemeDetail,
  id: 2,
  tags: null,
  category: null,
  description: null,
  rise_fall_pct: -1.5,
}

const mockThemeWithInsights: ThemeDetailResponse = {
  ...mockThemeDetail,
  profile: {
    definition: '机器人是可自动执行任务的机器系统。',
    core_logic: '需求增长与技术进步共同驱动。',
    applications: ['工业制造'],
    catalysts: ['政策支持'],
    risks: ['竞争加剧'],
    sources: [
      {
        title: '来源一',
        url: 'https://example.com/profile',
        publisher: '示例网',
        published_at: '2026-07-19T08:00:00Z',
      },
    ],
    generated_at: '2026-07-20T08:00:00Z',
  },
  recent_driver_events: [
    {
      id: 1,
      title: '机器人产业政策发布',
      summary: '支持机器人示范应用。',
      source: '示例网',
      url: 'https://example.com/event',
      published_at: '2026-07-20T08:00:00Z',
      relevance_score: 88,
      crawled_at: '2026-07-20T09:00:00Z',
    },
  ],
  market_snapshot: {
    trade_date: '2026-07-20',
    up_count: 12,
    down_count: 8,
    flat_count: 1,
    suspended_count: 2,
    limit_up_count: 3,
    limit_down_count: 1,
    calculated_at: '2026-07-20T09:00:00Z',
    up_down_ratio: 1.5,
    up_down_display: '12:8',
  },
}

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  })
}

function renderThemeDetail() {
  const queryClient = createQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/themes/1']}>
        <ThemeDetail />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

// --- Tests ---

describe('ThemeDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockLocationState = null
  })
  // 1. 加载状态
  describe('加载状态', () => {
    it('加载中显示骨架屏', () => {
      vi.mocked(fetchThemeDetail).mockReturnValue(new Promise(() => {}))
      renderThemeDetail()
      const skeletons = document.querySelectorAll('[class*=animate-pulse]')
      expect(skeletons.length).toBeGreaterThan(0)
    })
  })

  // 2. 错误状态
  describe('错误状态', () => {
    it('显示错误信息', async () => {
      vi.mocked(fetchThemeDetail).mockRejectedValue(new Error('网络错误'))
      renderThemeDetail()
      expect(await screen.findByText(/加载失败/)).toBeInTheDocument()
      expect(screen.getByText(/网络错误/)).toBeInTheDocument()
    })

    it('显示重试按钮', async () => {
      vi.mocked(fetchThemeDetail).mockRejectedValue(new Error('网络错误'))
      renderThemeDetail()
      expect(await screen.findByText('重试')).toBeInTheDocument()
    })

    it('点击重试按钮调用 refetch', async () => {
      const user = userEvent.setup()
      vi.mocked(fetchThemeDetail)
        .mockRejectedValueOnce(new Error('网络错误'))
        .mockResolvedValueOnce(mockThemeDetail)
      renderThemeDetail()
      const retryButton = await screen.findByText('重试')
      await user.click(retryButton)
      expect(vi.mocked(fetchThemeDetail)).toHaveBeenCalledTimes(2)
    })

    it('错误状态有返回按钮', async () => {
      vi.mocked(fetchThemeDetail).mockRejectedValue(new Error('fail'))
      renderThemeDetail()
      await screen.findByText(/加载失败/)
      const backButtons = screen.getAllByRole('button')
      expect(backButtons.length).toBeGreaterThan(0)
    })
  })

  // 3. 正常渲染
  describe('正常渲染', () => {
    it('显示题材名称', async () => {
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeDetail)
      renderThemeDetail()
      const names = await screen.findAllByText('人工智能')
      expect(names.length).toBeGreaterThanOrEqual(1)
    })

    it('显示题材分类', async () => {
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeDetail)
      renderThemeDetail()
      expect(await screen.findByText('科技')).toBeInTheDocument()
    })

    it('显示题材描述', async () => {
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeDetail)
      renderThemeDetail()
      expect(await screen.findByText(/AI 相关题材/)).toBeInTheDocument()
    })

    it('显示热度指数', async () => {
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeDetail)
      renderThemeDetail()
      expect(await screen.findByText('95.5')).toBeInTheDocument()
    })

    it('显示涨跌幅', async () => {
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeDetail)
      renderThemeDetail()
      expect(await screen.findByText('+2.35%')).toBeInTheDocument()
    })

    it('显示负涨跌幅', async () => {
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeNoTags)
      renderThemeDetail()
      expect(await screen.findByText('-1.50%')).toBeInTheDocument()
    })

    it('显示股票数量', async () => {
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeDetail)
      renderThemeDetail()
      expect(await screen.findByText('50')).toBeInTheDocument()
    })

    it('显示标签', async () => {
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeDetail)
      renderThemeDetail()
      expect(await screen.findByText('AI')).toBeInTheDocument()
      expect(screen.getByText('机器学习')).toBeInTheDocument()
      expect(screen.getByText('大模型')).toBeInTheDocument()
    })
  })

  // 4. 可选字段为空
  describe('可选字段为空', () => {
    it('无标签时不渲染标签区域', async () => {
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeNoTags)
      renderThemeDetail()
      await screen.findAllByText('人工智能')
      expect(screen.queryByText('机器学习')).not.toBeInTheDocument()
    })

    it('无分类时不显示分类标签', async () => {
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeNoTags)
      renderThemeDetail()
      await screen.findAllByText('人工智能')
      expect(screen.queryByText('科技')).not.toBeInTheDocument()
    })

    it('无描述时不显示描述文本', async () => {
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeNoTags)
      renderThemeDetail()
      await screen.findAllByText('人工智能')
      expect(screen.queryByText(/AI 相关题材/)).not.toBeInTheDocument()
    })
  })

  // 5. 图表区域
  describe('图表区域', () => {
    it('渲染热度趋势折线图', async () => {
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeDetail)
      renderThemeDetail()
      expect(await screen.findByTestId('heat-trend-line')).toBeInTheDocument()
    })

    it('热度趋势图有 7 个数据点', async () => {
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeDetail)
      renderThemeDetail()
      const chart = await screen.findByTestId('heat-trend-line')
      expect(chart.getAttribute('data-points')).toBe('7')
    })

    it('渲染产业链分布饼图', async () => {
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeDetail)
      renderThemeDetail()
      expect(await screen.findByTestId('industry-chain-pie')).toBeInTheDocument()
    })
  })

  // 6. 产业链区域
  describe('产业链区域', () => {
    it('渲染 IndustryChainSection 组件', async () => {
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeDetail)
      renderThemeDetail()
      expect(await screen.findByTestId('industry-chain-section')).toBeInTheDocument()
    })

    it('传递正确的 themeId', async () => {
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeDetail)
      renderThemeDetail()
      const section = await screen.findByTestId('industry-chain-section')
      expect(section.getAttribute('data-theme-id')).toBe('1')
    })
  })

  // 7. 导航
  describe('导航', () => {
    it('从主页进入时点击返回按钮导航到主页', async () => {
      const user = userEvent.setup()
      mockLocationState = { from: '/' }
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeDetail)
      renderThemeDetail()
      await screen.findAllByText('人工智能')
      const header = document.querySelector('header')
      const backButton = header?.querySelector('button')
      expect(backButton).toBeTruthy()
      await user.click(backButton!)
      expect(mockNavigate).toHaveBeenCalledWith('/')
    })

    it('从题材库进入时返回原来的分页和筛选地址', async () => {
      const user = userEvent.setup()
      mockLocationState = { from: '/themes?page=3&category=科技' }
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeDetail)
      renderThemeDetail()
      await screen.findAllByText('人工智能')
      const header = document.querySelector('header')
      const backButton = header?.querySelector('button')
      await user.click(backButton!)
      expect(mockNavigate).toHaveBeenCalledWith('/themes?page=3&category=科技')
    })

    it('直接打开详情页时返回题材库', async () => {
      const user = userEvent.setup()
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeDetail)
      renderThemeDetail()
      await screen.findAllByText('人工智能')
      const header = document.querySelector('header')
      const backButton = header?.querySelector('button')
      await user.click(backButton!)
      expect(mockNavigate).toHaveBeenCalledWith('/themes')
    })

    it('空状态时点击返回按钮导航到题材库', async () => {
      vi.mocked(fetchThemeDetail).mockResolvedValue(null as unknown as ThemeDetailResponse)
      renderThemeDetail()
      const backLink = await screen.findByText('返回题材库')
      await userEvent.click(backLink)
      expect(mockNavigate).toHaveBeenCalledWith('/themes')
    })
  })

  // 8. 刷新按钮
  describe('刷新按钮', () => {
    it('渲染刷新按钮', async () => {
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeDetail)
      renderThemeDetail()
      expect(await screen.findByText('刷新图谱')).toBeInTheDocument()
    })

    it('点击刷新按钮调用图谱刷新接口', async () => {
      const user = userEvent.setup()
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeDetail)
      vi.mocked(refreshConceptGraph).mockResolvedValue({
        theme_id: 1,
        theme_name: '人工智能',
        source_count: 3,
        added_nodes: 2,
        updated_nodes: 1,
        stock_links: 1,
        message: '图谱已根据公开资料增量更新',
      })
      renderThemeDetail()
      const refreshButton = await screen.findByText('刷新图谱')
      await user.click(refreshButton)
      expect(vi.mocked(refreshConceptGraph)).toHaveBeenCalledWith(1)
    })

    it('展示洞察区域并在刷新资料后重新获取详情', async () => {
      const user = userEvent.setup()
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeWithInsights)
      vi.mocked(refreshThemeInsights).mockResolvedValue({
        theme_id: 1,
        theme_name: '人工智能',
        profile_updated: true,
        candidate_events: 3,
        inserted_events: 1,
        updated_events: 0,
        ignored_events: 2,
        successful_sources: ['示例网'],
        failed_sources: ['DuckDuckGo'],
        degraded: false,
        refreshed_at: '2026-07-20T10:00:00Z',
        message: '题材资料已部分更新',
      })
      renderThemeDetail()

      const profileHeading = await screen.findByRole('heading', { name: '题材详细介绍' })
      const eventHeading = screen.getByRole('heading', { name: '最近驱动事件' })
      const sideRail = screen.getByTestId('theme-detail-side-rail')
      expect(
        profileHeading.compareDocumentPosition(eventHeading) & Node.DOCUMENT_POSITION_FOLLOWING
      ).toBeTruthy()
      expect(sideRail).toContainElement(eventHeading)

      await user.click(screen.getByRole('button', { name: '刷新题材资料' }))

      await waitFor(() => expect(fetchThemeDetail).toHaveBeenCalledTimes(2))
      expect(await screen.findByText(/失败来源：DuckDuckGo/)).toBeInTheDocument()
    })

    it('显示后端返回的资料刷新中文错误', async () => {
      const user = userEvent.setup()
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeDetail)
      vi.mocked(refreshThemeInsights).mockRejectedValue({
        response: { data: { detail: '未抓取到可验证的题材资料，原数据已保留' } },
      })
      renderThemeDetail()

      await user.click(await screen.findByRole('button', { name: '刷新题材资料' }))

      expect(await screen.findByText('未抓取到可验证的题材资料，原数据已保留')).toBeInTheDocument()
    })

    it('页头在窄屏使用纵向布局避免按钮横向溢出', async () => {
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeDetail)
      renderThemeDetail()

      expect(await screen.findByTestId('theme-detail-header')).toHaveClass('flex-col')
    })
  })

  // 9. 图表标题
  describe('图表标题', () => {
    it('显示热度趋势标题', async () => {
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeDetail)
      renderThemeDetail()
      expect(await screen.findByText('热度趋势')).toBeInTheDocument()
    })

    it('显示产业链分布标题', async () => {
      vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeDetail)
      renderThemeDetail()
      expect(await screen.findByText('产业链分布')).toBeInTheDocument()
    })
  })
})
