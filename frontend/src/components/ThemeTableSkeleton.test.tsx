/** ThemeTableSkeleton 组件测试 */

import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { ThemeTableSkeleton } from './ThemeTableSkeleton'

describe('ThemeTableSkeleton', () => {
  it('renders without crashing', () => {
    const { container } = render(<ThemeTableSkeleton />)
    expect(container.firstChild).toBeInTheDocument()
  })

  it('applies correct container classes', () => {
    const { container } = render(<ThemeTableSkeleton />)
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper).toHaveClass('w-full')
    expect(wrapper).toHaveClass('rounded-xl')
    expect(wrapper).toHaveClass('border')
    expect(wrapper).toHaveClass('border-border')
    expect(wrapper).toHaveClass('bg-card')
    expect(wrapper).toHaveClass('p-4')
  })

  it('renders left section with title and tag skeletons', () => {
    const { container } = render(<ThemeTableSkeleton />)
    const leftSection = container.querySelector('.min-w-0')
    expect(leftSection).toBeInTheDocument()
    expect(leftSection).toHaveClass('flex-1')

    // 左侧应该有两个子元素
    const children = leftSection?.children
    expect(children?.length).toBe(2)
  })

  it('renders right section with action skeletons', () => {
    const { container } = render(<ThemeTableSkeleton />)
    // 使用 querySelectorAll 获取所有flex items-center gap-4 容器，第二个是右供
    const flexContainers = container.querySelectorAll('.flex.items-center.gap-4')
    // 第一个匹配的是外层（名justify-between），第二个是右侧区域
    const rightSection = flexContainers[1]
    expect(rightSection).toBeInTheDocument()

    // 右侧应该有三个子元素
    const children = rightSection?.children
    expect(children?.length).toBe(3)
  })

  it('renders correct total number of skeleton elements', () => {
    const { container } = render(<ThemeTableSkeleton />)
    // Skeleton 组件的基础类是 bg-muted，使用[class*="bg-muted"] 匹配
    // 部分元素有rounded-full 会覆监rounded-xl，所以只用bg-muted
    const allSkeletons = container.querySelectorAll('[class*="bg-muted"]')
    // 左侧 2 不+ 右侧 3 不= 5 不
    expect(allSkeletons).toHaveLength(5)
  })

  it('renders with flex layout for horizontal arrangement', () => {
    const { container } = render(<ThemeTableSkeleton />)
    const flexContainer = container.querySelector('.flex.items-center.justify-between')
    expect(flexContainer).toBeInTheDocument()
  })

  it('is wrapped with React.memo', () => {
    expect(ThemeTableSkeleton.$$typeof).toBe(Symbol.for('react.memo'))
  })
})
