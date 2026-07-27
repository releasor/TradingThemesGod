/** 题材成分股区域测试 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ThemeConstituentStocks } from './ThemeConstituentStocks'

vi.mock('@/api/theme', () => ({
  fetchThemeStocks: vi.fn(),
}))

vi.mock('@/components/StockList', () => ({
  StockList: ({
    stocks,
    layout,
  }: {
    stocks: unknown[]
    layout?: string
  }) => (
    <div data-testid="stock-list" data-layout={layout ?? 'stack'}>
      {stocks.length} stocks
    </div>
  ),
}))

import { fetchThemeStocks } from '@/api/theme'

function renderSection(themeId = 7) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeConstituentStocks themeId={themeId} />
    </QueryClientProvider>
  )
}

describe('ThemeConstituentStocks', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('不依赖产业链，直接加载并展示题材成分股', async () => {
    vi.mocked(fetchThemeStocks).mockResolvedValue({
      items: [
        {
          id: 1,
          code: '000001',
          name: '平安银行',
          industry: '银行',
          market_cap: 100,
          current_price: 10,
          rise_fall_pct: 1.2,
          exchange: 'SZ',
        },
      ],
      total: 1,
      page: 1,
      page_size: 100,
      total_pages: 1,
    })

    renderSection()

    expect(await screen.findByText('全部成分股')).toBeInTheDocument()
    expect(await screen.findByTestId('stock-list')).toHaveTextContent('1 stocks')
    expect(screen.getByTestId('stock-list')).toHaveAttribute('data-layout', 'grid')
    expect(fetchThemeStocks).toHaveBeenCalledWith(7, undefined, 1, 100)
  })

  it('无成分股时显示明确空状态', async () => {
    vi.mocked(fetchThemeStocks).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 100,
      total_pages: 0,
    })

    renderSection()

    expect(await screen.findByText('暂无成分股数据')).toBeInTheDocument()
  })
})
