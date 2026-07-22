/** ChainPointCard 组件测试 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ChainPointCard } from './ChainPointCard'
import type { IndustryChainBrief } from '@/types/theme'

// 模拟 fetchThemeStocks
vi.mock('@/api/theme', () => ({
  fetchThemeStocks: vi.fn().mockResolvedValue({
    items: [
      { code: '000001', name: '平安银行', industry: '银行' },
      { code: '000002', name: '万科A', industry: '房地产' },
    ],
    total: 2,
    page: 1,
    page_size: 100,
  }),
}))

// 模拟 StockList
vi.mock('@/components/StockList', () => ({
  StockList: ({ stocks }: { stocks: unknown[] }) => (
    <div data-testid="stock-list">{stocks.length} stocks</div>
  ),
}))

// 模拟 StockListSkeleton
vi.mock('@/components/StockListSkeleton', () => ({
  StockListSkeleton: () => <div data-testid="stock-list-skeleton">loading...</div>,
}))

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  })
}

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = createQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  )
}

const baseChainPoint: IndustryChainBrief = {
  id: 1,
  name: '上游原材料',
  level: 'upstream',
  description: '芯片制造所需原材料供应商',
  representative_companies: ['公司A', '公司B'],
  sort_order: 1,
}

describe('ChainPointCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders chain point name', () => {
    renderWithQuery(<ChainPointCard chainPoint={baseChainPoint} themeId={1} />)
    expect(screen.getByText('上游原材料')).toBeInTheDocument()
  })

  it('renders description', () => {
    renderWithQuery(<ChainPointCard chainPoint={baseChainPoint} themeId={1} />)
    expect(screen.getByText('芯片制造所需原材料供应商')).toBeInTheDocument()
  })

  it('renders representative companies', () => {
    renderWithQuery(<ChainPointCard chainPoint={baseChainPoint} themeId={1} />)
    expect(screen.getByText('公司A')).toBeInTheDocument()
    expect(screen.getByText('公司B')).toBeInTheDocument()
  })

  it('does not render companies when list is empty', () => {
    const chainPoint = { ...baseChainPoint, representative_companies: [] }
    renderWithQuery(<ChainPointCard chainPoint={chainPoint} themeId={1} />)
    expect(screen.queryByText('公司A')).not.toBeInTheDocument()
  })

  it('does not render companies when null', () => {
    const chainPoint = { ...baseChainPoint, representative_companies: null as unknown as string[] }
    renderWithQuery(<ChainPointCard chainPoint={chainPoint} themeId={1} />)
    // 不应崩溃
    expect(screen.getByText('上游原材料')).toBeInTheDocument()
  })

  it('does not render description when not provided', () => {
    const chainPoint = { ...baseChainPoint, description: null }
    renderWithQuery(<ChainPointCard chainPoint={chainPoint} themeId={1} />)
    expect(screen.queryByText('芯片制造所需原材料供应商')).not.toBeInTheDocument()
  })

  it('starts collapsed', () => {
    renderWithQuery(<ChainPointCard chainPoint={baseChainPoint} themeId={1} />)
    expect(screen.queryByTestId('stock-list')).not.toBeInTheDocument()
    expect(screen.queryByTestId('stock-list-skeleton')).not.toBeInTheDocument()
  })

  it('has expand button with correct aria-label', () => {
    renderWithQuery(<ChainPointCard chainPoint={baseChainPoint} themeId={1} />)
    const expandBtn = screen.getByLabelText('展开')
    expect(expandBtn).toBeInTheDocument()
  })

  it('toggles to expanded state when button is clicked', () => {
    renderWithQuery(<ChainPointCard chainPoint={baseChainPoint} themeId={1} />)
    fireEvent.click(screen.getByLabelText('展开'))
    expect(screen.getByLabelText('折叠')).toBeInTheDocument()
  })

  it('handles representative_companies as object', () => {
    const chainPoint = {
      ...baseChainPoint,
      representative_companies: { 0: '公司X', 1: '公司Y' } as unknown as string[],
    }
    renderWithQuery(<ChainPointCard chainPoint={chainPoint} themeId={1} />)
    expect(screen.getByText('公司X')).toBeInTheDocument()
    expect(screen.getByText('公司Y')).toBeInTheDocument()
  })
})
