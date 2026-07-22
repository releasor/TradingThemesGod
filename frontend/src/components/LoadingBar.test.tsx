import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { LoadingBar } from './LoadingBar'

describe('LoadingBar', () => {
  it('renders nothing when isLoading is false', () => {
    const { container } = render(<LoadingBar isLoading={false} />)
    expect(container.innerHTML).toBe('')
  })

  it('renders loading bar when isLoading is true', () => {
    const { container } = render(<LoadingBar isLoading={true} />)
    expect(container.innerHTML).not.toBe('')
    // 检查是否有动画相关的元素
    const bar = container.querySelector('[style*="animation"]')
    expect(bar).toBeInTheDocument()
  })

  it('renders with correct animation style', () => {
    const { container } = render(<LoadingBar isLoading={true} />)
    const bar = container.querySelector('[style*="loading-bar"]')
    expect(bar).toBeInTheDocument()
  })

  it('renders with fixed positioning', () => {
    const { container } = render(<LoadingBar isLoading={true} />)
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper).toHaveClass('fixed')
    expect(wrapper).toHaveClass('top-0')
  })

  it('applies primary background color to bar', () => {
    const { container } = render(<LoadingBar isLoading={true} />)
    const bar = container.querySelector('.bg-primary')
    expect(bar).toBeInTheDocument()
  })
})
