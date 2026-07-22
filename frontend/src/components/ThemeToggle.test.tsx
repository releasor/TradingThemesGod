/** ThemeToggle 组件和 useTheme Hook 测试 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, renderHook, act } from '@testing-library/react'
import { ThemeToggle, useTheme } from './ThemeToggle'

// mock matchMedia
const mockMatchMedia = vi.fn()

beforeEach(() => {
  localStorage.clear()
  document.documentElement.classList.remove('light', 'dark')

  // 默认返回 light
  mockMatchMedia.mockReturnValue({
    matches: false,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  })
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: mockMatchMedia,
  })
})

afterEach(() => {
  document.documentElement.classList.remove('light', 'dark')
  localStorage.clear()
})

describe('useTheme hook', () => {
  it('returns system theme by default when no stored theme', () => {
    const { result } = renderHook(() => useTheme())
    expect(result.current.theme).toBe('system')
  })

  it('returns stored theme from localStorage', () => {
    localStorage.setItem('theme', 'dark')
    const { result } = renderHook(() => useTheme())
    expect(result.current.theme).toBe('dark')
  })

  it('sets theme and persists to localStorage', () => {
    const { result } = renderHook(() => useTheme())

    act(() => {
      result.current.setTheme('dark')
    })

    expect(result.current.theme).toBe('dark')
    expect(localStorage.getItem('theme')).toBe('dark')
  })

  it('sets light theme and applies it to DOM', () => {
    const { result } = renderHook(() => useTheme())

    act(() => {
      result.current.setTheme('light')
    })

    expect(result.current.theme).toBe('light')
    expect(document.documentElement.classList.contains('light')).toBe(true)
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('sets dark theme and applies it to DOM', () => {
    const { result } = renderHook(() => useTheme())

    act(() => {
      result.current.setTheme('dark')
    })

    expect(result.current.theme).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(document.documentElement.classList.contains('light')).toBe(false)
  })

  it('resolves system theme to light when system prefers light', () => {
    mockMatchMedia.mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })

    const { result } = renderHook(() => useTheme())

    act(() => {
      result.current.setTheme('system')
    })

    expect(result.current.theme).toBe('system')
    expect(document.documentElement.classList.contains('light')).toBe(true)
  })

  it('resolves system theme to dark when system prefers dark', () => {
    mockMatchMedia.mockReturnValue({
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })

    const { result } = renderHook(() => useTheme())

    act(() => {
      result.current.setTheme('system')
    })

    expect(result.current.theme).toBe('system')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('registers media query change listener for system theme', () => {
    const addEventListener = vi.fn()
    const removeEventListener = vi.fn()
    mockMatchMedia.mockReturnValue({
      matches: false,
      addEventListener,
      removeEventListener,
    })

    const { unmount } = renderHook(() => useTheme())

    expect(addEventListener).toHaveBeenCalledWith('change', expect.any(Function))

    unmount()
    expect(removeEventListener).toHaveBeenCalledWith('change', expect.any(Function))
  })

  it('cleans up previous theme classes when switching', () => {
    const { result } = renderHook(() => useTheme())

    act(() => {
      result.current.setTheme('dark')
    })
    expect(document.documentElement.classList.contains('dark')).toBe(true)

    act(() => {
      result.current.setTheme('light')
    })
    expect(document.documentElement.classList.contains('light')).toBe(true)
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })
})

describe('ThemeToggle component', () => {
  it('renders three theme buttons', () => {
    render(<ThemeToggle />)
    const buttons = screen.getAllByRole('button')
    expect(buttons).toHaveLength(3)
  })

  it('renders buttons with correct titles', () => {
    render(<ThemeToggle />)
    expect(screen.getByTitle('亮色')).toBeInTheDocument()
    expect(screen.getByTitle('暗色')).toBeInTheDocument()
    expect(screen.getByTitle('系统')).toBeInTheDocument()
  })

  it('highlights the active theme button', () => {
    render(<ThemeToggle />)
    // 默认 system 应该高亮
    const systemButton = screen.getByTitle('系统')
    expect(systemButton.className).toContain('bg-primary')
  })

  it('switches theme when button is clicked', () => {
    render(<ThemeToggle />)

    fireEvent.click(screen.getByTitle('暗色'))
    expect(localStorage.getItem('theme')).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('applies custom className', () => {
    const { container } = render(<ThemeToggle className="my-class" />)
    expect(container.firstChild).toHaveClass('my-class')
  })

  it('switches from light to dark to system', () => {
    render(<ThemeToggle />)

    fireEvent.click(screen.getByTitle('亮色'))
    expect(document.documentElement.classList.contains('light')).toBe(true)

    fireEvent.click(screen.getByTitle('暗色'))
    expect(document.documentElement.classList.contains('dark')).toBe(true)

    fireEvent.click(screen.getByTitle('系统'))
    expect(localStorage.getItem('theme')).toBe('system')
  })
})
