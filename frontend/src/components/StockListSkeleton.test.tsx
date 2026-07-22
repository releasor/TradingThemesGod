/** StockListSkeleton 组件测试 */

import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { StockListSkeleton } from './StockListSkeleton'

describe('StockListSkeleton', () => {
  it('renders without crashing', () => {
    const { container } = render(<StockListSkeleton />)
    expect(container.firstChild).toBeInTheDocument()
  })

  it('applies correct container classes', () => {
    const { container } = render(<StockListSkeleton />)
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper).toHaveClass('space-y-1')
  })

  it('renders exactly 3 skeleton rows', () => {
    const { container } = render(<StockListSkeleton />)
    const rows = container.querySelectorAll('.flex.items-center.justify-between.rounded-xl')
    expect(rows).toHaveLength(3)
  })

  it('renders skeleton items with correct structure', () => {
    const { container } = render(<StockListSkeleton />)
    const rows = container.querySelectorAll('.flex.items-center.justify-between.rounded-xl')

    rows.forEach((row) => {
      // 每行应有左侧区域（包含两不Skeleton）和右侧区域（一不Skeleton，
      const leftSection = row.querySelector('.flex.items-center.gap-2')
      expect(leftSection).toBeInTheDocument()
    })
  })

  it('is wrapped with React.memo', () => {
    expect(StockListSkeleton.$$typeof).toBe(Symbol.for('react.memo'))
  })
})
