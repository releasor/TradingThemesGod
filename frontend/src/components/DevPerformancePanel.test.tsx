/** DevPerformancePanel 组件测试 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { DevPerformancePanel } from './DevPerformancePanel'
import * as webVitals from 'web-vitals'

// Mock lucide-react 图标组件
vi.mock('lucide-react', () => ({
  Activity: (props: Record<string, unknown>) => <span data-testid="activity-icon" {...props} />,
  X: (props: Record<string, unknown>) => <span data-testid="x-icon" {...props} />,
}))

// Mock @/lib/utils
vi.mock('@/lib/utils', () => ({
  cn: (...args: string[]) => args.filter(Boolean).join(' '),
}))

// Mock @/lib/web-vitals
vi.mock('@/lib/web-vitals', () => ({
  getMetricRating: vi.fn((name: string, value: number) => {
    const thresholds: Record<string, [number, number]> = {
      LCP: [2500, 4000],
      INP: [200, 500],
      CLS: [0.1, 0.25],
      FCP: [1800, 3000],
      TTFB: [800, 1800],
    }
    const [good, needsImprovement] = thresholds[name] || [0, 0]
    if (value <= good) return 'good'
    if (value <= needsImprovement) return 'needs-improvement'
    return 'poor'
  }),
}))

// 存储 web-vitals 的回调函数，用于测试时手动触发
const metricCallbacks: Record<string, (metric: { name: string; value: number }) => void> = {}

// Mock web-vitals 动态导入
vi.mock('web-vitals', () => ({
  onLCP: vi.fn((cb: (metric: { name: string; value: number }) => void) => {
    metricCallbacks.LCP = cb
  }),
  onINP: vi.fn((cb: (metric: { name: string; value: number }) => void) => {
    metricCallbacks.INP = cb
  }),
  onCLS: vi.fn((cb: (metric: { name: string; value: number }) => void) => {
    metricCallbacks.CLS = cb
  }),
  onFCP: vi.fn((cb: (metric: { name: string; value: number }) => void) => {
    metricCallbacks.FCP = cb
  }),
  onTTFB: vi.fn((cb: (metric: { name: string; value: number }) => void) => {
    metricCallbacks.TTFB = cb
  }),
}))

describe('DevPerformancePanel', () => {
  beforeEach(() => {
    // 清理回调
    Object.keys(metricCallbacks).forEach((key) => delete metricCallbacks[key])
  })

  it('渲染触发按钮', () => {
    render(<DevPerformancePanel />)
    const button = screen.getByTitle('性能监控')
    expect(button).toBeInTheDocument()
  })

  it('按钮包含 Activity 图标', () => {
    render(<DevPerformancePanel />)
    expect(screen.getByTestId('activity-icon')).toBeInTheDocument()
  })

  it('初始状态面板未展开', () => {
    render(<DevPerformancePanel />)
    expect(screen.queryByText('Web Vitals')).not.toBeInTheDocument()
  })

  it('点击按钮展开面板', () => {
    render(<DevPerformancePanel />)
    fireEvent.click(screen.getByTitle('性能监控'))
    expect(screen.getByText('Web Vitals')).toBeInTheDocument()
  })

  it('面板无指标时显示加载中', () => {
    render(<DevPerformancePanel />)
    fireEvent.click(screen.getByTitle('性能监控'))
    expect(screen.getByText('加载中...')).toBeInTheDocument()
  })

  it('面板显示关闭按钮', () => {
    render(<DevPerformancePanel />)
    fireEvent.click(screen.getByTitle('性能监控'))
    const closeButtons = screen.getAllByTestId('x-icon')
    expect(closeButtons.length).toBeGreaterThanOrEqual(1)
  })

  it('点击关闭按钮收起面板', () => {
    render(<DevPerformancePanel />)
    fireEvent.click(screen.getByTitle('性能监控'))
    expect(screen.getByText('Web Vitals')).toBeInTheDocument()

    // 点击 X 图标的父按钮
    const xIcon = screen.getByTestId('x-icon')
    const closeButton = xIcon.closest('button')!
    fireEvent.click(closeButton)

    expect(screen.queryByText('Web Vitals')).not.toBeInTheDocument()
  })

  it('再次点击触发按钮可收起面板', () => {
    render(<DevPerformancePanel />)
    const triggerButton = screen.getByTitle('性能监控')

    // 展开
    fireEvent.click(triggerButton)
    expect(screen.getByText('Web Vitals')).toBeInTheDocument()

    // 收起
    fireEvent.click(triggerButton)
    expect(screen.queryByText('Web Vitals')).not.toBeInTheDocument()
  })

  it('面板显示颜色图例', () => {
    render(<DevPerformancePanel />)
    fireEvent.click(screen.getByTitle('性能监控'))
    expect(screen.getByText('Good')).toBeInTheDocument()
    expect(screen.getByText('OK')).toBeInTheDocument()
    expect(screen.getByText('Poor')).toBeInTheDocument()
  })

  it('动态导入 web-vitals 后注册所有指标监听', async () => {
    render(<DevPerformancePanel />)

    await waitFor(() => {
      expect(webVitals.onLCP).toHaveBeenCalled()
      expect(webVitals.onINP).toHaveBeenCalled()
      expect(webVitals.onCLS).toHaveBeenCalled()
      expect(webVitals.onFCP).toHaveBeenCalled()
      expect(webVitals.onTTFB).toHaveBeenCalled()
    })
  })

  it('收到指标数据后在面板中显示', async () => {
    render(<DevPerformancePanel />)
    fireEvent.click(screen.getByTitle('性能监控'))

    // 等待动态导入完成
    await waitFor(() => {
      expect(Object.keys(metricCallbacks)).toContain('LCP')
    })

    // 模拟发送 LCP 指标
    act(() => {
      metricCallbacks.LCP({ name: 'LCP', value: 1500 })
    })

    await waitFor(() => {
      expect(screen.getByText('LCP')).toBeInTheDocument()
      expect(screen.getByText('1500ms')).toBeInTheDocument()
    })
  })

  it('收到 CLS 指标时显示小数格式', async () => {
    render(<DevPerformancePanel />)
    fireEvent.click(screen.getByTitle('性能监控'))

    await waitFor(() => {
      expect(Object.keys(metricCallbacks)).toContain('CLS')
    })

    act(() => {
      metricCallbacks.CLS({ name: 'CLS', value: 0.05 })
    })

    await waitFor(() => {
      expect(screen.getByText('CLS')).toBeInTheDocument()
      expect(screen.getByText('0.050')).toBeInTheDocument()
    })
  })

  it('同一指标多次更新只保留最新值', async () => {
    render(<DevPerformancePanel />)
    fireEvent.click(screen.getByTitle('性能监控'))

    await waitFor(() => {
      expect(Object.keys(metricCallbacks)).toContain('LCP')
    })

    // 第一次报告
    act(() => {
      metricCallbacks.LCP({ name: 'LCP', value: 1500 })
    })

    await waitFor(() => {
      expect(screen.getByText('1500ms')).toBeInTheDocument()
    })

    // 第二次报告，更新值
    act(() => {
      metricCallbacks.LCP({ name: 'LCP', value: 2000 })
    })

    await waitFor(() => {
      expect(screen.getByText('2000ms')).toBeInTheDocument()
    })

    // 应该只有一个 LCP 条目
    const lcpLabels = screen.getAllByText('LCP')
    expect(lcpLabels).toHaveLength(1)
  })

  it('收到多个不同指标时全部显示', async () => {
    render(<DevPerformancePanel />)
    fireEvent.click(screen.getByTitle('性能监控'))

    await waitFor(() => {
      expect(Object.keys(metricCallbacks)).toContain('LCP')
    })

    act(() => {
      metricCallbacks.LCP({ name: 'LCP', value: 1500 })
      metricCallbacks.FCP({ name: 'FCP', value: 800 })
    })

    await waitFor(() => {
      expect(screen.getByText('LCP')).toBeInTheDocument()
      expect(screen.getByText('1500ms')).toBeInTheDocument()
      expect(screen.getByText('FCP')).toBeInTheDocument()
      expect(screen.getByText('800ms')).toBeInTheDocument()
    })
  })
})
