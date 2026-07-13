/** IndustryChainPie 组件测试 */

import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { IndustryChainPie } from './IndustryChainPie'
import type { IndustryChainBrief } from '@/types/theme'

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
  PieChart: {},
}))

vi.mock('echarts/components', () => ({
  TooltipComponent: {},
  LegendComponent: {},
}))

vi.mock('echarts/renderers', () => ({
  CanvasRenderer: {},
}))

const mockChains = {
  upstream: [
    { id: 1, level: 'upstream' as const, name: '芯片设计', description: null, representative_companies: null, sort_order: 1 },
    { id: 2, level: 'upstream' as const, name: '晶圆制造', description: null, representative_companies: null, sort_order: 2 },
  ],
  midstream: [
    { id: 3, level: 'midstream' as const, name: '封装测试', description: null, representative_companies: null, sort_order: 1 },
  ],
  downstream: [
    { id: 4, level: 'downstream' as const, name: '终端应用', description: null, representative_companies: null, sort_order: 1 },
    { id: 5, level: 'downstream' as const, name: '系统集成', description: null, representative_companies: null, sort_order: 2 },
    { id: 6, level: 'downstream' as const, name: '售后服务', description: null, representative_companies: null, sort_order: 3 },
  ],
}

describe('IndustryChainPie', () => {
  it('renders chart when chains provided', () => {
    render(<IndustryChainPie chains={mockChains} />)
    expect(screen.getByTestId('echarts-mock')).toBeInTheDocument()
  })

  it('renders empty state when no chains', () => {
    render(
      <IndustryChainPie
        chains={{ upstream: [], midstream: [], downstream: [] }}
      />
    )
    expect(screen.getByText('暂无数据')).toBeInTheDocument()
  })

  it('renders chart when only some levels have data', () => {
    render(
      <IndustryChainPie
        chains={{
          upstream: mockChains.upstream,
          midstream: [],
          downstream: [],
        }}
      />
    )
    expect(screen.getByTestId('echarts-mock')).toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(
      <IndustryChainPie chains={mockChains} className="custom-class" />
    )
    expect(container.firstChild).toHaveClass('custom-class')
  })
})
