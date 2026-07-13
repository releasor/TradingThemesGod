/** EmptyChart 组件测试 */

import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { EmptyChart } from './EmptyChart'

describe('EmptyChart', () => {
  it('renders default message', () => {
    render(<EmptyChart />)
    expect(screen.getByText('暂无数据')).toBeInTheDocument()
  })

  it('renders custom message', () => {
    render(<EmptyChart message="无历史数据" />)
    expect(screen.getByText('无历史数据')).toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(<EmptyChart className="custom-class" />)
    expect(container.firstChild).toHaveClass('custom-class')
  })

  it('renders inbox icon', () => {
    const { container } = render(<EmptyChart />)
    expect(container.querySelector('svg')).toBeInTheDocument()
  })
})
