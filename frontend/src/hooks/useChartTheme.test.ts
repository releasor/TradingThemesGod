import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useChartTheme } from './useChartTheme'

describe('useChartTheme', () => {
  beforeEach(() => {
    // 确保每次测试前清除 dark class
    document.documentElement.classList.remove('dark')
  })

  afterEach(() => {
    document.documentElement.classList.remove('dark')
  })

  it('returns light theme colors by default', () => {
    const { result } = renderHook(() => useChartTheme())

    expect(result.current.isDark).toBe(false)
    expect(result.current.colors.textColor).toBe('#374151')
    expect(result.current.colors.secondaryTextColor).toBe('#6b7280')
    expect(result.current.colors.gridBorderColor).toBe('#e5e7eb')
    expect(result.current.colors.backgroundColor).toBe('transparent')
    expect(result.current.colors.tooltipBg).toBe('#ffffff')
    expect(result.current.colors.tooltipTextColor).toBe('#374151')
    expect(result.current.colors.tooltipBorderColor).toBe('#e5e7eb')
  })

  it('returns dark theme colors when dark class is present', () => {
    document.documentElement.classList.add('dark')

    const { result } = renderHook(() => useChartTheme())

    expect(result.current.isDark).toBe(true)
    expect(result.current.colors.textColor).toBe('#e5e7eb')
    expect(result.current.colors.secondaryTextColor).toBe('#9ca3af')
    expect(result.current.colors.gridBorderColor).toBe('#374151')
    expect(result.current.colors.backgroundColor).toBe('transparent')
    expect(result.current.colors.tooltipBg).toBe('#1f2937')
    expect(result.current.colors.tooltipTextColor).toBe('#e5e7eb')
    expect(result.current.colors.tooltipBorderColor).toBe('#4b5563')
  })

  it('updates when dark mode is toggled', async () => {
    const { result } = renderHook(() => useChartTheme())

    expect(result.current.isDark).toBe(false)

    act(() => {
      document.documentElement.classList.add('dark')
    })

    // MutationObserver 异步触发，需 waitFor
    await waitFor(() => {
      expect(result.current.isDark).toBe(true)
    })
    expect(result.current.colors.tooltipBg).toBe('#1f2937')

    act(() => {
      document.documentElement.classList.remove('dark')
    })

    await waitFor(() => {
      expect(result.current.isDark).toBe(false)
    })
    expect(result.current.colors.tooltipBg).toBe('#ffffff')
  })

  it('memoizes colors when isDark does not change', () => {
    const { result } = renderHook(() => useChartTheme())

    const colors1 = result.current.colors

    // colors 引用应保持不变（useMemo）—— 不改变 dark 状态
    expect(result.current.colors).toBe(colors1)
    expect(result.current.colors.textColor).toBe('#374151')
  })
})
