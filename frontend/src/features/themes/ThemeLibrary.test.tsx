/** ThemeLibrary 题材库主页面测试 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeLibrary } from './ThemeLibrary'
import type { ThemeBrief } from '@/types/theme'

// --- Mocks ---

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

vi.mock('@/api/theme', () => ({
  fetchThemes: vi.fn(),
  fetchCategories: vi.fn(),
  refreshConceptGraph: vi.fn(),
}))

vi.mock('@/hooks/useThemeFilters', () => ({
  useThemeFilters: vi.fn(),
}))

vi.mock('@/components/FilterBar', () => ({
  FilterBar: () => <div data-testid="filter-bar" />,
}))

vi.mock('@/components/SortSelect', () => ({
  SortSelect: () => <div data-testid="sort-select" />,
}))

vi.mock('@/components/ExportButton', () => ({
  ExportButton: () => <button data-testid="export-button">导出</button>,
}))

vi.mock('@/components/ThemeTableRow', () => ({
  ThemeTableRow: ({ theme, onClick }: { theme: ThemeBrief; onClick: () => void }) => (
    <button
      data-testid={`theme-row-${theme.id}`}
      aria-label={`查看题材详情: ${theme.name}`}
      onClick={onClick}
    >
      {theme.name}
    </button>
  ),
}))

vi.mock('@/components/ThemeTableSkeleton', () => ({
  ThemeTableSkeleton: () => <div data-testid="theme-skeleton" />,
}))

vi.mock('@/components/Pagination', () => ({
  Pagination: ({
    page,
    totalPages,
    onPageChange,
  }: {
    page: number
    totalPages: number
    onPageChange: (p: number) => void
  }) => (
    <nav data-testid="pagination" aria-label="分页导航">
      <span>
        第 {page} / {totalPages} 页
      </span>
      <button onClick={() => onPageChange(page + 1)}>下一页</button>
    </nav>
  ),
}))

// --- Imports after mocks ---

import { fetchThemes, fetchCategories, refreshConceptGraph } from '@/api/theme'
import { useThemeFilters } from '@/hooks/useThemeFilters'

// --- Fixtures ---

const mockThemes: ThemeBrief[] = [
  {
    id: 1,
    name: '人工智能',
    code: 'AI',
    description: 'AI 相关题材',
    heat_index: 95.5,
    rise_fall_pct: 2.35,
    stock_count: 50,
    category: '科技',
    tags: ['AI', '机器学习'],
    source: '东方财富',
  },
  {
    id: 2,
    name: '新能源汽车',
    code: 'NEV',
    description: null,
    heat_index: 80.2,
    rise_fall_pct: -1.2,
    stock_count: 30,
    category: '汽车',
    tags: null,
    source: null,
  },
]

const defaultFiltersReturn = {
  filters: {
    page: 1,
    page_size: 20,
    sort_by: 'heat_index' as const,
    sort_order: 'desc' as const,
  },
  searchInput: '',
  setSearchInput: vi.fn(),
  updateFilter: vi.fn(),
  setPage: vi.fn(),
  setSort: vi.fn(),
  clearFilters: vi.fn(),
  activeFilterCount: 0,
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

function renderThemeLibrary() {
  const queryClient = createQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/themes?page=3&category=%E7%A7%91%E6%8A%80']}>
        <ThemeLibrary />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

// --- Tests ---

describe('ThemeLibrary', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useThemeFilters).mockReturnValue({ ...defaultFiltersReturn })
    vi.mocked(fetchCategories).mockResolvedValue({ categories: ['科技', '汽车'] })
  })

  it('点击品牌标题返回主页', async () => {
    vi.mocked(fetchThemes).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 0,
    })
    renderThemeLibrary()

    await userEvent.click(screen.getByRole('button', { name: '返回主页' }))

    expect(mockNavigate).toHaveBeenCalledWith('/')
  })

  it('逐个更新图谱并展示成功、失败和最终汇总', async () => {
    vi.mocked(fetchThemes).mockResolvedValue({
      items: mockThemes,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    })
    vi.mocked(refreshConceptGraph)
      .mockResolvedValueOnce({
        theme_id: 1,
        theme_name: '人工智能',
        source_count: 6,
        added_nodes: 12,
        updated_nodes: 3,
        stock_links: 8,
        message: '更新完成',
      })
      .mockRejectedValueOnce({
        response: { data: { detail: '模型服务未配置' } },
      })
    renderThemeLibrary()

    await userEvent.click(await screen.findByRole('button', { name: '更新本页前 5 个图谱' }))

    expect(await screen.findByText('来源 6，新增 12，更新 3，股票关联 8')).toBeInTheDocument()
    expect(await screen.findByText('模型服务未配置；已有图谱已保留')).toBeInTheDocument()
    expect(screen.getByText('更新完成：成功 1 个，失败 1 个')).toBeInTheDocument()
    expect(refreshConceptGraph).toHaveBeenNthCalledWith(1, 1)
    expect(refreshConceptGraph).toHaveBeenNthCalledWith(2, 2)
  })

  it('图谱刷新超时时展示后端返回的具体处理建议', async () => {
    vi.mocked(fetchThemes).mockResolvedValue({
      items: mockThemes.slice(0, 1),
      total: 1,
      page: 1,
      page_size: 20,
      total_pages: 1,
    })
    vi.mocked(refreshConceptGraph).mockRejectedValueOnce({
      response: {
        data: {
          detail: '模型抽取图谱失败：模型响应超时，请调高超时时间或更换响应更快的模型',
        },
      },
    })
    renderThemeLibrary()

    await userEvent.click(await screen.findByRole('button', { name: '更新本页前 5 个图谱' }))

    expect(
      await screen.findByText(
        '模型抽取图谱失败：模型响应超时，请调高超时时间或更换响应更快的模型；已有图谱已保留'
      )
    ).toBeInTheDocument()
    expect(screen.getByText('更新完成：成功 0 个，失败 1 个')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '检查模型设置' })).toBeInTheDocument()
  })

  it('更新耗时时显示当前题材和执行进度', async () => {
    vi.mocked(fetchThemes).mockResolvedValue({
      items: mockThemes,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    })
    let resolveRefresh: ((value: {
      theme_id: number
      theme_name: string
      source_count: number
      added_nodes: number
      updated_nodes: number
      stock_links: number
      message: string
    }) => void) | undefined
    vi.mocked(refreshConceptGraph).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveRefresh = resolve
      })
    )
    renderThemeLibrary()

    await userEvent.click(await screen.findByRole('button', { name: '更新本页前 5 个图谱' }))

    expect(screen.getByRole('button', { name: '正在更新 1/2' })).toBeDisabled()
    expect(screen.getByText('正在分析：人工智能')).toBeInTheDocument()

    resolveRefresh?.({
      theme_id: 1,
      theme_name: '人工智能',
      source_count: 1,
      added_nodes: 1,
      updated_nodes: 0,
      stock_links: 0,
      message: '完成',
    })
    await waitFor(() => expect(refreshConceptGraph).toHaveBeenCalledWith(2))
  })

  // 1. 页头渲染
  describe('页头渲染', () => {
    it('渲染页面标题 TradingThemesGod', () => {
      vi.mocked(fetchThemes).mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      })
      renderThemeLibrary()
      expect(screen.getByText('TradingThemesGod')).toBeInTheDocument()
    })

    it('渲染副标题 题材库', () => {
      vi.mocked(fetchThemes).mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      })
      renderThemeLibrary()
      expect(screen.getByText('题材库')).toBeInTheDocument()
    })
  })

  // 2. 加载状态
  describe('加载状态', () => {
    it('加载中显示骨架屏', () => {
      vi.mocked(fetchThemes).mockReturnValue(new Promise(() => {}))
      renderThemeLibrary()
      const skeletons = screen.getAllByTestId('theme-skeleton')
      expect(skeletons).toHaveLength(10)
    })

    it('加载完成后隐藏骨架屏', async () => {
      vi.mocked(fetchThemes).mockResolvedValue({
        items: mockThemes,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      })
      renderThemeLibrary()
      expect(await screen.findByText('人工智能')).toBeInTheDocument()
      expect(screen.queryAllByTestId('theme-skeleton')).toHaveLength(0)
    })
  })

  // 3. 错误状态
  describe('错误状态', () => {
    it('显示错误信息', async () => {
      vi.mocked(fetchThemes).mockRejectedValue(new Error('网络错误'))
      renderThemeLibrary()
      expect(await screen.findByText(/加载失败/)).toBeInTheDocument()
      expect(screen.getByText(/网络错误/)).toBeInTheDocument()
    })

    it('显示重试按钮', async () => {
      vi.mocked(fetchThemes).mockRejectedValue(new Error('网络错误'))
      renderThemeLibrary()
      expect(await screen.findByText('重试')).toBeInTheDocument()
    })

    it('点击重试按钮调用 refetch', async () => {
      const user = userEvent.setup()
      vi.mocked(fetchThemes).mockRejectedValueOnce(new Error('网络错误')).mockResolvedValueOnce({
        items: mockThemes,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      })
      renderThemeLibrary()
      const retryButton = await screen.findByText('重试')
      await user.click(retryButton)
      expect(vi.mocked(fetchThemes)).toHaveBeenCalledTimes(2)
    })
  })

  // 4. 空状态
  describe('空状态', () => {
    it('无筛选条件时显示暂无数据', async () => {
      vi.mocked(fetchThemes).mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      })
      renderThemeLibrary()
      expect(await screen.findByText('暂无题材数据')).toBeInTheDocument()
    })

    it('有筛选条件时显示无匹配结果', async () => {
      vi.mocked(useThemeFilters).mockReturnValue({
        ...defaultFiltersReturn,
        activeFilterCount: 2,
      })
      vi.mocked(fetchThemes).mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      })
      renderThemeLibrary()
      expect(await screen.findByText('没有匹配当前筛选条件的题材')).toBeInTheDocument()
    })

    it('有筛选条件时显示清除筛选按钮', async () => {
      vi.mocked(useThemeFilters).mockReturnValue({
        ...defaultFiltersReturn,
        activeFilterCount: 1,
      })
      vi.mocked(fetchThemes).mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      })
      renderThemeLibrary()
      expect(await screen.findByText('清除筛选条件')).toBeInTheDocument()
    })

    it('无筛选条件时隐藏清除筛选按钮', async () => {
      vi.mocked(fetchThemes).mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      })
      renderThemeLibrary()
      await screen.findByText('暂无题材数据')
      expect(screen.queryByText('清除筛选条件')).not.toBeInTheDocument()
    })
  })

  // 5. 题材列表渲染
  describe('题材列表渲染', () => {
    it('渲染所有题材行', async () => {
      vi.mocked(fetchThemes).mockResolvedValue({
        items: mockThemes,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      })
      renderThemeLibrary()
      expect(await screen.findByText('人工智能')).toBeInTheDocument()
      expect(screen.getByText('新能源汽车')).toBeInTheDocument()
    })

    it('每个题材行有正确的 aria-label', async () => {
      vi.mocked(fetchThemes).mockResolvedValue({
        items: mockThemes,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      })
      renderThemeLibrary()
      expect(await screen.findByLabelText('查看题材详情: 人工智能')).toBeInTheDocument()
      expect(screen.getByLabelText('查看题材详情: 新能源汽车')).toBeInTheDocument()
    })
  })

  // 6. 总数显示
  describe('总数显示', () => {
    it('显示题材总数', async () => {
      vi.mocked(fetchThemes).mockResolvedValue({
        items: mockThemes,
        total: 42,
        page: 1,
        page_size: 20,
        total_pages: 3,
      })
      renderThemeLibrary()
      expect(await screen.findByText('42')).toBeInTheDocument()
      expect(screen.getByText(/个题材/)).toBeInTheDocument()
    })

    it('搜索时显示搜索关键词', async () => {
      vi.mocked(useThemeFilters).mockReturnValue({
        ...defaultFiltersReturn,
        filters: { ...defaultFiltersReturn.filters, q: 'AI' },
      })
      vi.mocked(fetchThemes).mockResolvedValue({
        items: mockThemes,
        total: 5,
        page: 1,
        page_size: 20,
        total_pages: 1,
      })
      renderThemeLibrary()
      expect(await screen.findByText(/搜索/)).toBeInTheDocument()
      expect(screen.getByText(/AI/)).toBeInTheDocument()
    })

    it('选择分类时显示分类名', async () => {
      vi.mocked(useThemeFilters).mockReturnValue({
        ...defaultFiltersReturn,
        filters: { ...defaultFiltersReturn.filters, category: '科技' },
      })
      vi.mocked(fetchThemes).mockResolvedValue({
        items: mockThemes,
        total: 10,
        page: 1,
        page_size: 20,
        total_pages: 1,
      })
      renderThemeLibrary()
      expect(await screen.findByText(/分类: 科技/)).toBeInTheDocument()
    })
  })

  // 7. 导航到看板
  describe('导航到看板', () => {
    it('点击看板按钮导航到首页', async () => {
      const user = userEvent.setup()
      vi.mocked(fetchThemes).mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      })
      renderThemeLibrary()
      const dashboardButton = await screen.findByText('看板')
      await user.click(dashboardButton)
      expect(mockNavigate).toHaveBeenCalledWith('/')
    })
  })

  // 8. 导航到题材详情
  describe('导航到题材详情', () => {
    it('点击题材行导航到详情页', async () => {
      const user = userEvent.setup()
      vi.mocked(fetchThemes).mockResolvedValue({
        items: mockThemes,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      })
      renderThemeLibrary()
      const themeRow = await screen.findByLabelText('查看题材详情: 人工智能')
      await user.click(themeRow)
      expect(mockNavigate).toHaveBeenCalledWith('/themes/1', {
        state: { from: '/themes?page=3&category=%E7%A7%91%E6%8A%80' },
      })
    })

    it('不同题材行导航到不同详情页', async () => {
      const user = userEvent.setup()
      vi.mocked(fetchThemes).mockResolvedValue({
        items: mockThemes,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      })
      renderThemeLibrary()
      const themeRow = await screen.findByLabelText('查看题材详情: 新能源汽车')
      await user.click(themeRow)
      expect(mockNavigate).toHaveBeenCalledWith('/themes/2', {
        state: { from: '/themes?page=3&category=%E7%A7%91%E6%8A%80' },
      })
    })
  })

  // 9. 分页逻辑
  describe('分页', () => {
    it('多页时显示分页组件', async () => {
      vi.mocked(fetchThemes).mockResolvedValue({
        items: mockThemes,
        total: 40,
        page: 1,
        page_size: 20,
        total_pages: 2,
      })
      renderThemeLibrary()
      expect(await screen.findByTestId('pagination')).toBeInTheDocument()
    })

    it('单页时隐藏分页组件', async () => {
      vi.mocked(fetchThemes).mockResolvedValue({
        items: mockThemes,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      })
      renderThemeLibrary()
      await screen.findByText('人工智能')
      expect(screen.queryByTestId('pagination')).not.toBeInTheDocument()
    })

    it('加载中不显示分页', () => {
      vi.mocked(fetchThemes).mockReturnValue(new Promise(() => {}))
      renderThemeLibrary()
      expect(screen.queryByTestId('pagination')).not.toBeInTheDocument()
    })

    it('错误状态不显示分页', async () => {
      vi.mocked(fetchThemes).mockRejectedValue(new Error('fail'))
      renderThemeLibrary()
      await screen.findByText(/加载失败/)
      expect(screen.queryByTestId('pagination')).not.toBeInTheDocument()
    })
  })

  // 10. FilterBar 和 SortSelect
  describe('筛选和排序组件', () => {
    it('渲染 FilterBar 组件', async () => {
      vi.mocked(fetchThemes).mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      })
      renderThemeLibrary()
      expect(await screen.findByTestId('filter-bar')).toBeInTheDocument()
    })

    it('渲染 SortSelect 组件', async () => {
      vi.mocked(fetchThemes).mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      })
      renderThemeLibrary()
      expect(await screen.findByTestId('sort-select')).toBeInTheDocument()
    })
  })

  // 11. ExportButton
  describe('导出按钮', () => {
    it('渲染 ExportButton 组件', async () => {
      vi.mocked(fetchThemes).mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      })
      renderThemeLibrary()
      expect(await screen.findByTestId('export-button')).toBeInTheDocument()
    })
  })

  // 12. 刷新按钮
  describe('刷新按钮', () => {
    it('渲染刷新按钮', async () => {
      vi.mocked(fetchThemes).mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      })
      renderThemeLibrary()
      expect(await screen.findByText('刷新')).toBeInTheDocument()
    })

    it('点击刷新按钮调用 refetch', async () => {
      const user = userEvent.setup()
      vi.mocked(fetchThemes).mockResolvedValue({
        items: mockThemes,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      })
      renderThemeLibrary()
      const refreshButton = await screen.findByText('刷新')
      await user.click(refreshButton)
      expect(vi.mocked(fetchThemes)).toHaveBeenCalledTimes(2)
    })
  })
})
