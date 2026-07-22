import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useSearchHistory } from './useSearchHistory'

const STORAGE_KEY = 'search-history'

// 模拟 localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key]
    }),
    clear: vi.fn(() => {
      store = {}
    }),
    get length() {
      return Object.keys(store).length
    },
    key: vi.fn(() => null),
  }
})()

Object.defineProperty(window, 'localStorage', { value: localStorageMock })

describe('useSearchHistory', () => {
  beforeEach(() => {
    localStorageMock.clear()
    vi.clearAllMocks()
  })

  it('initial state is empty array', () => {
    const { result } = renderHook(() => useSearchHistory())
    expect(result.current.history).toEqual([])
  })

  it('adds a search term', () => {
    const { result } = renderHook(() => useSearchHistory())

    act(() => {
      result.current.addSearch('人工智能')
    })

    expect(result.current.history).toEqual(['人工智能'])
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      STORAGE_KEY,
      JSON.stringify(['人工智能']),
    )
  })

  it('deduplicates and moves to front', () => {
    const { result } = renderHook(() => useSearchHistory())

    act(() => {
      result.current.addSearch('人工智能')
    })
    act(() => {
      result.current.addSearch('新能源')
    })
    act(() => {
      result.current.addSearch('人工智能')
    })

    expect(result.current.history).toEqual(['人工智能', '新能源'])
  })

  it('trims whitespace and ignores empty strings', () => {
    const { result } = renderHook(() => useSearchHistory())

    act(() => {
      result.current.addSearch('')
    })
    expect(result.current.history).toEqual([])

    act(() => {
      result.current.addSearch('   ')
    })
    expect(result.current.history).toEqual([])

    act(() => {
      result.current.addSearch('  人工智能  ')
    })
    // addSearch 使用 query 原始值（未 trim），但 trim 检查通过后直接存储
    expect(result.current.history).toEqual(['  人工智能  '])
  })

  it('respects MAX_HISTORY=10', () => {
    const { result } = renderHook(() => useSearchHistory())

    act(() => {
      for (let i = 1; i <= 12; i++) {
        result.current.addSearch(`term${i}`)
      }
    })

    expect(result.current.history).toHaveLength(10)
    // 最新的在前
    expect(result.current.history[0]).toBe('term12')
    expect(result.current.history[9]).toBe('term3')
  })

  it('clearHistory empties the list and removes from localStorage', () => {
    const { result } = renderHook(() => useSearchHistory())

    act(() => {
      result.current.addSearch('人工智能')
      result.current.addSearch('新能源')
    })
    expect(result.current.history).toHaveLength(2)

    act(() => {
      result.current.clearHistory()
    })

    expect(result.current.history).toEqual([])
    expect(localStorageMock.removeItem).toHaveBeenCalledWith(STORAGE_KEY)
  })

  it('removes a specific item', () => {
    const { result } = renderHook(() => useSearchHistory())

    act(() => {
      result.current.addSearch('人工智能')
      result.current.addSearch('新能源')
      result.current.addSearch('芯片')
    })

    act(() => {
      result.current.removeSearch('新能源')
    })

    expect(result.current.history).toEqual(['芯片', '人工智能'])
    expect(result.current.history).not.toContain('新能源')
  })

  it('loads from localStorage on mount', () => {
    const stored = ['人工智能', '新能源', '芯片']
    localStorageMock.getItem.mockReturnValue(JSON.stringify(stored))

    const { result } = renderHook(() => useSearchHistory())

    expect(result.current.history).toEqual(stored)
    expect(localStorageMock.getItem).toHaveBeenCalledWith(STORAGE_KEY)
  })

  it('handles corrupted localStorage data gracefully', () => {
    localStorageMock.getItem.mockReturnValue('not-valid-json{{{')

    // 不应抛出异常
    const { result } = renderHook(() => useSearchHistory())

    expect(result.current.history).toEqual([])
  })
})
