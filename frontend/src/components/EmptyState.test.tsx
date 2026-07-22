/** EmptyState 组件测试 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { EmptyState } from './EmptyState'

describe('EmptyState', () => {
  it('renders default no-data state', () => {
    render(<EmptyState />)
    expect(screen.getByText('暂无数据')).toBeInTheDocument()
    expect(screen.getByText('还没有任何数据，稍后再来看看吧')).toBeInTheDocument()
  })

  it('renders no-results state', () => {
    render(<EmptyState type="no-results" />)
    expect(screen.getByText('未找到结果')).toBeInTheDocument()
    expect(screen.getByText('没有找到匹配的结果，试试其他关键词')).toBeInTheDocument()
  })

  it('renders error state', () => {
    render(<EmptyState type="error" />)
    expect(screen.getByText('加载失败')).toBeInTheDocument()
    expect(screen.getByText('数据加载出错了，请稍后重试')).toBeInTheDocument()
  })

  it('renders no-content state', () => {
    render(<EmptyState type="no-content" />)
    expect(screen.getByText('内容为空')).toBeInTheDocument()
    expect(screen.getByText('这里还没有内容')).toBeInTheDocument()
  })

  it('renders custom state', () => {
    render(<EmptyState type="custom" title="自定义标题" description="自定义描述" />)
    expect(screen.getByText('自定义标题')).toBeInTheDocument()
    expect(screen.getByText('自定义描述')).toBeInTheDocument()
  })

  it('renders custom title overriding default', () => {
    render(<EmptyState title="自定义标题" />)
    expect(screen.getByText('自定义标题')).toBeInTheDocument()
    expect(screen.queryByText('暂无数据')).not.toBeInTheDocument()
  })

  it('renders custom description overriding default', () => {
    render(<EmptyState description="自定义描述" />)
    expect(screen.getByText('自定义描述')).toBeInTheDocument()
    expect(screen.queryByText('还没有任何数据，稍后再来看看吧')).not.toBeInTheDocument()
  })

  it('renders action when provided', () => {
    render(
      <EmptyState
        action={<button>开始采集</button>}
      />
    )
    expect(screen.getByText('开始采集')).toBeInTheDocument()
  })

  it('does not render action when not provided', () => {
    render(<EmptyState />)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(<EmptyState className="custom-class" />)
    expect(container.firstChild).toHaveClass('custom-class')
  })

  it('renders icon for each type', () => {
    const { container, rerender } = render(<EmptyState type="no-data" />)
    expect(container.querySelector('svg')).toBeInTheDocument()

    rerender(<EmptyState type="no-results" />)
    expect(container.querySelector('svg')).toBeInTheDocument()

    rerender(<EmptyState type="error" />)
    expect(container.querySelector('svg')).toBeInTheDocument()

    rerender(<EmptyState type="no-content" />)
    expect(container.querySelector('svg')).toBeInTheDocument()
  })
})
