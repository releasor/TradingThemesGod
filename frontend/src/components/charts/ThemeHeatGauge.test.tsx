/** ThemeHeatGauge 组件测试 */

import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ThemeHeatGauge } from './ThemeHeatGauge'

// Mock echarts-for-react
vi.mock('echarts-for-react/lib/core', () => ({
  default: vi.fn(({ style, opts }) => (
    <div data-testid="echarts-mock" style={style} data-renderer={opts?.renderer} />
  )),
}))

// Mock echarts core
vi.mock('echarts/core', () => ({
  use: vi.fn(),
}))

// Mock echarts charts/components
vi.mock('echarts/charts', () => ({
  GaugeChart: {},
}))

vi.mock('echarts/renderers', () => ({
  CanvasRenderer: {},
}))

// Mock useChartTheme hook
vi.mock('@/hooks/useChartTheme', () => ({
  useChartTheme: () => ({
    colors: {
      textColor: '#333',
      secondaryTextColor: '#666',
    },
    isDark: false,
  }),
}))

describe('ThemeHeatGauge', () => {
  it('渲染图表组件', () => {
    render(<ThemeHeatGauge value={75} />)
    expect(screen.getByTestId('echarts-mock')).toBeInTheDocument()
  })

  it('应用自定义 className', () => {
    const { container } = render(
      <ThemeHeatGauge value={85} className="custom-class" />
    )
    expect(container.firstChild).toHaveClass('custom-class')
  })

  it('使用 canvas 渲染器', () => {
    render(<ThemeHeatGauge value={50} />)
    const chart = screen.getByTestId('echarts-mock')
    expect(chart).toHaveAttribute('data-renderer', 'canvas')
  })

  it('设置正确的图表样式高度', () => {
    render(<ThemeHeatGauge value={60} />)
    const chart = screen.getByTestId('echarts-mock')
    expect(chart).toHaveStyle({ height: '250px', width: '100%' })
  })
})
