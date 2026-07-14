/** ScrollToTop 组件测试 */

import { render } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ScrollToTop } from './ScrollToTop'

// Mock react-router-dom 的 useLocation
let mockPathname = '/'
vi.mock('react-router-dom', () => ({
  useLocation: () => ({ pathname: mockPathname }),
}))

describe('ScrollToTop', () => {
  let scrollToSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    scrollToSpy = vi.spyOn(window, 'scrollTo').mockImplementation(() => {})
    mockPathname = '/'
  })

  it('组件挂载时调用 window.scrollTo(0, 0)', () => {
    render(<ScrollToTop />)
    expect(scrollToSpy).toHaveBeenCalledWith(0, 0)
  })

  it('返回 null，不渲染任何 DOM 元素', () => {
    const { container } = render(<ScrollToTop />)
    expect(container.firstChild).toBeNull()
  })

  it('路由路径变化时再次调用 scrollTo(0, 0)', () => {
    scrollToSpy.mockClear()
    const { rerender } = render(<ScrollToTop />)
    const initialCallCount = scrollToSpy.mock.calls.length

    // 模拟路由变化
    mockPathname = '/theme/123'
    rerender(<ScrollToTop />)
    expect(scrollToSpy.mock.calls.length).toBeGreaterThan(initialCallCount)
    expect(scrollToSpy).toHaveBeenLastCalledWith(0, 0)
  })
})
