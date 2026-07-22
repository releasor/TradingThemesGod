import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { useThemeFilters } from './useThemeFilters'
import { StrictMode, type ReactNode } from 'react'

function wrapper({ children }: { children: ReactNode }) {
  return <MemoryRouter>{children}</MemoryRouter>
}

function wrapperWithInitialEntries(entries: string[]) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <MemoryRouter initialEntries={entries}>{children}</MemoryRouter>
  }
}

describe('useThemeFilters', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns default filters when URL has no params', () => {
    const { result } = renderHook(() => useThemeFilters(), { wrapper })

    expect(result.current.filters.page).toBe(1)
    expect(result.current.filters.page_size).toBe(20)
    expect(result.current.filters.sort_by).toBe('heat_index')
    expect(result.current.filters.sort_order).toBe('desc')
    expect(result.current.filters.category).toBeUndefined()
    expect(result.current.filters.tags).toBeUndefined()
    expect(result.current.filters.q).toBeUndefined()
  })

  it('parses URL search params correctly', () => {
    const Wrapper = wrapperWithInitialEntries([
      '/?page=3&page_size=10&sort_by=name&sort_order=asc&category=AI&tags=热门',
    ])
    const { result } = renderHook(() => useThemeFilters(), { wrapper: Wrapper })

    expect(result.current.filters.page).toBe(3)
    expect(result.current.filters.page_size).toBe(10)
    expect(result.current.filters.sort_by).toBe('name')
    expect(result.current.filters.sort_order).toBe('asc')
    expect(result.current.filters.category).toBe('AI')
    expect(result.current.filters.tags).toBe('热门')
  })

  it('parses search query from URL', () => {
    const Wrapper = wrapperWithInitialEntries(['/?q=人工智能'])
    const { result } = renderHook(() => useThemeFilters(), { wrapper: Wrapper })

    expect(result.current.filters.q).toBe('人工智能')
    expect(result.current.searchInput).toBe('人工智能')
  })

  it('updateFilter sets a filter value', () => {
    const { result } = renderHook(() => useThemeFilters(), { wrapper })

    act(() => {
      result.current.updateFilter('category', 'AI')
    })

    expect(result.current.filters.category).toBe('AI')
  })

  it('updateFilter resets page to 1 when changing non-page filter', () => {
    const Wrapper = wrapperWithInitialEntries(['/?page=5'])
    const { result } = renderHook(() => useThemeFilters(), { wrapper: Wrapper })

    expect(result.current.filters.page).toBe(5)

    act(() => {
      result.current.updateFilter('category', 'AI')
    })

    expect(result.current.filters.page).toBe(1)
  })

  it('updateFilter does not reset page when changing page itself', () => {
    const { result } = renderHook(() => useThemeFilters(), { wrapper })

    act(() => {
      result.current.updateFilter('page', '3')
    })

    expect(result.current.filters.page).toBe(3)
  })

  it('updateFilter with undefined removes the param', () => {
    const Wrapper = wrapperWithInitialEntries(['/?category=AI'])
    const { result } = renderHook(() => useThemeFilters(), { wrapper: Wrapper })

    expect(result.current.filters.category).toBe('AI')

    act(() => {
      result.current.updateFilter('category', undefined)
    })

    expect(result.current.filters.category).toBeUndefined()
  })

  it('setPage updates the page number', () => {
    const { result } = renderHook(() => useThemeFilters(), { wrapper })

    act(() => {
      result.current.setPage(3)
    })

    expect(result.current.filters.page).toBe(3)
  })

  it('setSort updates sort_by, sort_order and resets page', () => {
    const Wrapper = wrapperWithInitialEntries(['/?page=5'])
    const { result } = renderHook(() => useThemeFilters(), { wrapper: Wrapper })

    act(() => {
      result.current.setSort('name', 'asc')
    })

    expect(result.current.filters.sort_by).toBe('name')
    expect(result.current.filters.sort_order).toBe('asc')
    expect(result.current.filters.page).toBe(1)
  })

  it('clearFilters resets all filters and search input', () => {
    const Wrapper = wrapperWithInitialEntries([
      '/?page=3&category=AI&q=test',
    ])
    const { result } = renderHook(() => useThemeFilters(), { wrapper: Wrapper })

    expect(result.current.filters.category).toBe('AI')

    act(() => {
      result.current.clearFilters()
    })

    expect(result.current.searchInput).toBe('')
    expect(result.current.filters.page).toBe(1)
    expect(result.current.filters.category).toBeUndefined()
    expect(result.current.filters.q).toBeUndefined()
  })

  it('activeFilterCount counts active filters', () => {
    const { result } = renderHook(() => useThemeFilters(), { wrapper })

    expect(result.current.activeFilterCount).toBe(0)

    act(() => {
      result.current.updateFilter('category', 'AI')
    })
    expect(result.current.activeFilterCount).toBe(1)

    act(() => {
      result.current.updateFilter('tags', '热门')
    })
    expect(result.current.activeFilterCount).toBe(2)
  })

  it('search debounce: updates searchInput immediately but delays URL update', () => {
    const { result } = renderHook(() => useThemeFilters(), { wrapper })

    act(() => {
      result.current.setSearchInput('test')
    })

    // searchInput 更新即时
    expect(result.current.searchInput).toBe('test')

    // URL 参数尚未更新（防抖中）
    expect(result.current.filters.q).toBeUndefined()

    // 推进防抖时间
    act(() => {
      vi.advanceTimersByTime(300)
    })

    // 防抖结束后 URL 更新
    expect(result.current.filters.q).toBe('test')
  })

  it('search debounce: resets page to 1', () => {
    const Wrapper = wrapperWithInitialEntries(['/?page=5'])
    const { result } = renderHook(() => useThemeFilters(), { wrapper: Wrapper })

    act(() => {
      result.current.setSearchInput('test')
    })

    act(() => {
      vi.advanceTimersByTime(300)
    })

    expect(result.current.filters.page).toBe(1)
  })

  it('preserves URL page when search input has not changed', () => {
    function Wrapper({ children }: { children: ReactNode }) {
      return (
        <StrictMode>
          <MemoryRouter initialEntries={['/?page=5']}>{children}</MemoryRouter>
        </StrictMode>
      )
    }
    const { result } = renderHook(() => useThemeFilters(), { wrapper: Wrapper })

    act(() => {
      vi.advanceTimersByTime(300)
    })

    expect(result.current.filters.page).toBe(5)
  })

  it('search debounce: clears q when searchInput is emptied', () => {
    const Wrapper = wrapperWithInitialEntries(['/?q=old'])
    const { result } = renderHook(() => useThemeFilters(), { wrapper: Wrapper })

    act(() => {
      result.current.setSearchInput('')
    })

    act(() => {
      vi.advanceTimersByTime(300)
    })

    expect(result.current.filters.q).toBeUndefined()
  })
})
