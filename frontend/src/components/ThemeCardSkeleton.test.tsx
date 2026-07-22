/** ThemeCardSkeleton 组件测试 */

import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { ThemeCardSkeleton } from './ThemeCardSkeleton'

describe('ThemeCardSkeleton', () => {
  it('renders without crashing', () => {
    const { container } = render(<ThemeCardSkeleton />)
    expect(container.firstChild).toBeInTheDocument()
  })

  it('applies correct container classes', () => {
    const { container } = render(<ThemeCardSkeleton />)
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper).toHaveClass('w-full')
    expect(wrapper).toHaveClass('rounded-xl')
    expect(wrapper).toHaveClass('border')
    expect(wrapper).toHaveClass('border-border')
    expect(wrapper).toHaveClass('bg-card')
    expect(wrapper).toHaveClass('p-3')
    expect(wrapper).toHaveClass('animate-pulse')
  })

  it('renders title skeleton placeholder', () => {
    const { container } = render(<ThemeCardSkeleton />)
    // 标题骨架：h-4、rounded-xl、bg-muted
    const titleSkeleton = container.querySelector('[class*="h-4"][class*="bg-muted"]')
    expect(titleSkeleton).toBeInTheDocument()
    expect(titleSkeleton).toHaveClass('rounded-xl')
  })

  it('renders heat tag skeleton placeholder', () => {
    const { container } = render(<ThemeCardSkeleton />)
    // 热度标签骨架：h-5、rounded-full、bg-muted
    const heatTagSkeleton = container.querySelector('[class*="h-5"][class*="rounded-full"][class*="bg-muted"]')
    expect(heatTagSkeleton).toBeInTheDocument()
  })

  it('renders bottom info skeleton placeholders', () => {
    const { container } = render(<ThemeCardSkeleton />)
    const bottomSection = container.querySelector('.mt-3')
    expect(bottomSection).toBeInTheDocument()
    expect(bottomSection).toHaveClass('flex')
    expect(bottomSection).toHaveClass('items-center')
    expect(bottomSection).toHaveClass('justify-between')

    // 检查底部两个骨架元索
    const skeletonElements = bottomSection?.querySelectorAll('[class*="bg-muted"]')
    expect(skeletonElements).toHaveLength(2)
  })

  it('renders correct number of skeleton elements', () => {
    const { container } = render(<ThemeCardSkeleton />)
    const skeletonElements = container.querySelectorAll('[class*="bg-muted"]')
    // 标题 + 热度标签 + 底部两个 = 4不
    expect(skeletonElements).toHaveLength(4)
  })

  it('is wrapped with React.memo', () => {
    // React.memo 组件具有 $$typeof 属态
    expect(ThemeCardSkeleton.$$typeof).toBe(Symbol.for('react.memo'))
  })

  it('maintains consistent structure across re-renders', () => {
    const { container, rerender } = render(<ThemeCardSkeleton />)
    const firstRenderHtml = container.innerHTML

    rerender(<ThemeCardSkeleton />)
    expect(container.innerHTML).toBe(firstRenderHtml)
  })
})
