import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StockList } from './StockList'
import type { StockBrief } from '@/types/stock'

// 模拟 StockPopover 组件（避免内部依赖复杂性）
vi.mock('@/components/StockPopover', () => ({
  StockPopover: ({ children, stock }: { children: React.ReactNode; stock: { code: string } }) => (
    <div data-testid={`stock-popover-${stock.code}`}>{children}</div>
  ),
}))

describe('StockList', () => {
  const mockStocks: StockBrief[] = [
    {
      code: '000001',
      name: '平安银行',
      rise_fall_pct: 3.5,
      industry: '金融',
    },
    {
      code: '600519',
      name: '贵州茅台',
      rise_fall_pct: -1.2,
      industry: '白酒',
    },
    {
      code: '000858',
      name: '五粮液',
      rise_fall_pct: 0,
      industry: '白酒',
    },
    {
      code: '300750',
      name: '宁德时代',
      rise_fall_pct: null as unknown as number,
      industry: '新能源',
    },
  ] as StockBrief[]

  it('renders empty state when stocks array is empty', () => {
    render(<StockList stocks={[]} />)
    expect(screen.getByText('暂无关联股票')).toBeInTheDocument()
  })

  it('renders stock names', () => {
    render(<StockList stocks={mockStocks} />)
    expect(screen.getByText('平安银行')).toBeInTheDocument()
    expect(screen.getByText('贵州茅台')).toBeInTheDocument()
    expect(screen.getByText('五粮液')).toBeInTheDocument()
    expect(screen.getByText('宁德时代')).toBeInTheDocument()
  })

  it('renders stock codes', () => {
    render(<StockList stocks={mockStocks} />)
    expect(screen.getByText('000001')).toBeInTheDocument()
    expect(screen.getByText('600519')).toBeInTheDocument()
    expect(screen.getByText('000858')).toBeInTheDocument()
    expect(screen.getByText('300750')).toBeInTheDocument()
  })

  it('renders correct number of stock items', () => {
    render(<StockList stocks={mockStocks} />)
    // 每个股票都有一个 popover 容器
    const items = screen.getAllByTestId(/stock-popover-/)
    expect(items).toHaveLength(4)
  })

  it('renders single stock correctly', () => {
    const singleStock = [mockStocks[0]]
    render(<StockList stocks={singleStock} />)
    expect(screen.getByText('平安银行')).toBeInTheDocument()
    expect(screen.getByText('000001')).toBeInTheDocument()
  })
})
