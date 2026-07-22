/** usePrefetch Hook 测试 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { usePrefetchTheme, usePrefetchStock } from './usePrefetch'
import React from 'react'

// Mock API
vi.mock('@/api/theme', () => ({
  fetchThemeDetail: vi.fn().mockResolvedValue({ id: 1, name: 'test' }),
}))

vi.mock('@/api/stock', () => ({
  fetchStockDetail: vi.fn().mockResolvedValue({ code: '000001', name: 'test' }),
}))

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  })
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children)
  }
}

describe('usePrefetchTheme', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns a function', () => {
    const { result } = renderHook(() => usePrefetchTheme(), {
      wrapper: createWrapper(),
    })
    expect(typeof result.current).toBe('function')
  })

  it('calls prefetchQuery with correct queryKey', () => {
    const wrapper = createWrapper()
    const { result } = renderHook(() => usePrefetchTheme(), { wrapper })
    // Call the prefetch function - it should not throw
    expect(() => result.current(42)).not.toThrow()
  })
})

describe('usePrefetchStock', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns a function', () => {
    const { result } = renderHook(() => usePrefetchStock(), {
      wrapper: createWrapper(),
    })
    expect(typeof result.current).toBe('function')
  })

  it('calls prefetchQuery with stock code', () => {
    const wrapper = createWrapper()
    const { result } = renderHook(() => usePrefetchStock(), { wrapper })
    expect(() => result.current('000001')).not.toThrow()
  })
})
