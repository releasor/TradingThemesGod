/** ThemeHeatTrendLine 组件测试 */

import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ThemeHeatTrendLine } from './ThemeHeatTrendLine'

// Mock echarts-for-react
vi.mock('echarts-for-react/lib/core', () => ({
  default: vi.fn(({ style }) => (
    <div data-testid="echarts-mock" style={style} />
  )),
}))

// Mock echarts core
vi.mock('echarts/core', () => ({
  use: vi.fn(),
}))

// Mock echarts charts/components
vi.mock('echarts/charts', () => ({
  LineChart: {},
}))

vi.mock('echarts/components', () => ({
  GridComponent: {},
  TooltipComponent: {},
  LegendComponent: {},
}))

vi.mock('echarts/renderers', () => ({
  CanvasRenderer: {},
}))

const mockData = [
  { date: '2024-01-01', value: 75 },
  { date: '2024-01-02', value: 80 },
  { date: '2024-01-03', value: 65 },
]

describe('ThemeHeatTrendLine', () => {
  it('renders chart when data provided', () => {
    render(<ThemeHeatTrendLine data={mockData} />)
    expect(screen.getByTestId('echarts-mock')).toBeInTheDocument()
  })

  it('renders empty state when no data', () => {
    render(<ThemeHeatTrendLine data={[]} />)
    expect(screen.getByText('暂无数据')).toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(
      <ThemeHeatTrendLine data={mockData} className="custom-class" />
    )
    expect(container.firstChild).toHaveClass('custom-class')
  })
})
