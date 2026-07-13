/** ThemeRiseFallBar 组件测试 */

import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ThemeRiseFallBar } from './ThemeRiseFallBar'
import type { ThemeBrief } from '@/types/theme'

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
  BarChart: {},
}))

vi.mock('echarts/components', () => ({
  GridComponent: {},
  TooltipComponent: {},
  LegendComponent: {},
}))

vi.mock('echarts/renderers', () => ({
  CanvasRenderer: {},
}))

const mockThemes: ThemeBrief[] = [
  {
    id: 1,
    name: '人工智能',
    code: 'AI',
    description: null,
    heat_index: 95,
    rise_fall_pct: 5.23,
    stock_count: 50,
    category: '科技',
    tags: null,
    source: null,
  },
  {
    id: 2,
    name: '新能源',
    code: 'NE',
    description: null,
    heat_index: 88,
    rise_fall_pct: -2.15,
    stock_count: 30,
    category: '能源',
    tags: null,
    source: null,
  },
  {
    id: 3,
    name: '半导体',
    code: 'SC',
    description: null,
    heat_index: 82,
    rise_fall_pct: 0,
    stock_count: 25,
    category: '科技',
    tags: null,
    source: null,
  },
]

describe('ThemeRiseFallBar', () => {
  it('renders chart when themes provided', () => {
    render(<ThemeRiseFallBar themes={mockThemes} />)
    expect(screen.getByTestId('echarts-mock')).toBeInTheDocument()
  })

  it('renders empty state when no themes', () => {
    render(<ThemeRiseFallBar themes={[]} />)
    expect(screen.getByText('暂无数据')).toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(
      <ThemeRiseFallBar themes={mockThemes} className="custom-class" />
    )
    expect(container.firstChild).toHaveClass('custom-class')
  })
})
