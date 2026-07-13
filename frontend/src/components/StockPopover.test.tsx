/** StockPopover 组件测试 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StockPopover } from './StockPopover'
import type { StockBrief } from '@/types/stock'

// Mock fetchStockDetail
vi.mock('@/api/stock', () => ({
  fetchStockDetail: vi.fn(),
}))

import { fetchStockDetail } from '@/api/stock'

const mockStock: StockBrief = {
  id: 1,
  code: '000001',
  name: '平安银行',
  industry: '银行',
  market_cap: 2000_0000_0000,
  current_price: 12.50,
  rise_fall_pct: 2.35,
  exchange: 'SZ',
}

const mockStockDetail = {
  ...mockStock,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  recent_events: [
    {
      id: 1,
      title: '平安银行发布2024年年报',
      content: null,
      source: '东方财富',
      event_type: '财报',
      published_at: '2024-03-15T00:00:00Z',
    },
    {
      id: 2,
      title: '平安银行获得监管批准',
      content: null,
      source: '新浪财经',
      event_type: '公告',
      published_at: '2024-02-10T00:00:00Z',
    },
  ],
}

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })
}

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = createQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  )
}

describe('StockPopover', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders trigger element', () => {
    renderWithQuery(
      <StockPopover stock={mockStock}>
        <button>点击打开</button>
      </StockPopover>
    )

    expect(screen.getByText('点击打开')).toBeInTheDocument()
  })

  it('shows loading state when opened', async () => {
    vi.mocked(fetchStockDetail).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    const user = userEvent.setup()
    renderWithQuery(
      <StockPopover stock={mockStock}>
        <button>点击打开</button>
      </StockPopover>
    )

    await user.click(screen.getByText('点击打开'))

    await waitFor(() => {
      // Should show loading skeletons
      expect(document.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0)
    })
  })

  it('fetches stock detail when opened', async () => {
    vi.mocked(fetchStockDetail).mockResolvedValue(mockStockDetail)

    const user = userEvent.setup()
    renderWithQuery(
      <StockPopover stock={mockStock}>
        <button>点击打开</button>
      </StockPopover>
    )

    await user.click(screen.getByText('点击打开'))

    await waitFor(() => {
      expect(fetchStockDetail).toHaveBeenCalledWith('000001')
    })
  })

  it('does not fetch stock detail when closed', () => {
    renderWithQuery(
      <StockPopover stock={mockStock}>
        <button>点击打开</button>
      </StockPopover>
    )

    expect(fetchStockDetail).not.toHaveBeenCalled()
  })
})
