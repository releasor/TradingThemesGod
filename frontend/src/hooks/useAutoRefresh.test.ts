import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useAutoRefresh } from './useAutoRefresh'

describe('useAutoRefresh', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('starts with auto-refresh disabled by default', () => {
    const { result } = renderHook(() =>
      useAutoRefresh({ interval: 1000, onRefresh: vi.fn() }),
    )

    expect(result.current.isAutoRefresh).toBe(false)
  })

  it('starts with auto-refresh enabled when enabled=true', () => {
    const { result } = renderHook(() =>
      useAutoRefresh({ interval: 1000, enabled: true, onRefresh: vi.fn() }),
    )

    expect(result.current.isAutoRefresh).toBe(true)
  })

  it('toggles auto-refresh on and off', () => {
    const { result } = renderHook(() =>
      useAutoRefresh({ interval: 1000, onRefresh: vi.fn() }),
    )

    act(() => {
      result.current.toggleAutoRefresh()
    })
    expect(result.current.isAutoRefresh).toBe(true)

    act(() => {
      result.current.toggleAutoRefresh()
    })
    expect(result.current.isAutoRefresh).toBe(false)
  })

  it('calls onRefresh at the specified interval', () => {
    const onRefresh = vi.fn()
    renderHook(() =>
      useAutoRefresh({ interval: 1000, enabled: true, onRefresh }),
    )

    expect(onRefresh).not.toHaveBeenCalled()

    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(onRefresh).toHaveBeenCalledTimes(1)

    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(onRefresh).toHaveBeenCalledTimes(2)

    act(() => {
      vi.advanceTimersByTime(3000)
    })
    expect(onRefresh).toHaveBeenCalledTimes(5)
  })

  it('stops calling onRefresh when auto-refresh is disabled', () => {
    const onRefresh = vi.fn()
    const { result } = renderHook(() =>
      useAutoRefresh({ interval: 1000, enabled: true, onRefresh }),
    )

    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(onRefresh).toHaveBeenCalledTimes(1)

    act(() => {
      result.current.toggleAutoRefresh()
    })

    act(() => {
      vi.advanceTimersByTime(5000)
    })
    expect(onRefresh).toHaveBeenCalledTimes(1)
  })

  it('setAutoRefresh enables and disables', () => {
    const { result } = renderHook(() =>
      useAutoRefresh({ interval: 1000, onRefresh: vi.fn() }),
    )

    act(() => {
      result.current.setAutoRefresh(true)
    })
    expect(result.current.isAutoRefresh).toBe(true)

    act(() => {
      result.current.setAutoRefresh(false)
    })
    expect(result.current.isAutoRefresh).toBe(false)
  })

  it('setRefreshInterval changes the interval', () => {
    const onRefresh = vi.fn()
    const { result } = renderHook(() =>
      useAutoRefresh({ interval: 1000, enabled: true, onRefresh }),
    )

    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(onRefresh).toHaveBeenCalledTimes(1)

    act(() => {
      result.current.setRefreshInterval(2000)
    })

    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(onRefresh).toHaveBeenCalledTimes(1)

    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(onRefresh).toHaveBeenCalledTimes(2)
  })

  it('uses latest onRefresh callback', () => {
    const onRefresh1 = vi.fn()
    const onRefresh2 = vi.fn()
    const { rerender } = renderHook(
      ({ onRefresh }) =>
        useAutoRefresh({ interval: 1000, enabled: true, onRefresh }),
      { initialProps: { onRefresh: onRefresh1 } },
    )

    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(onRefresh1).toHaveBeenCalledTimes(1)

    rerender({ onRefresh: onRefresh2 })

    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(onRefresh2).toHaveBeenCalledTimes(1)
    expect(onRefresh1).toHaveBeenCalledTimes(1)
  })

  it('returns the configured interval', () => {
    const { result } = renderHook(() =>
      useAutoRefresh({ interval: 30000, onRefresh: vi.fn() }),
    )

    expect(result.current.refreshInterval).toBe(30000)
  })

  it('cleans up timer on unmount', () => {
    const onRefresh = vi.fn()
    const { unmount } = renderHook(() =>
      useAutoRefresh({ interval: 1000, enabled: true, onRefresh }),
    )

    unmount()

    act(() => {
      vi.advanceTimersByTime(5000)
    })
    expect(onRefresh).not.toHaveBeenCalled()
  })
})
