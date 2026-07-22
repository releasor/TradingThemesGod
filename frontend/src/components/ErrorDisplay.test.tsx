/** ErrorDisplay 组件测试 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ErrorDisplay } from './ErrorDisplay'

describe('ErrorDisplay', () => {
  it('renders network error message', () => {
    render(<ErrorDisplay errorType="network" />)
    expect(screen.getByText('网络连接失败')).toBeInTheDocument()
  })

  it('renders timeout error message', () => {
    render(<ErrorDisplay errorType="timeout" />)
    expect(screen.getByText('请求超时')).toBeInTheDocument()
  })

  it('renders server error message', () => {
    render(<ErrorDisplay errorType="server" />)
    expect(screen.getByText('服务器错误')).toBeInTheDocument()
  })

  it('renders not-found error message', () => {
    render(<ErrorDisplay errorType="not-found" />)
    expect(screen.getByText('资源不存在')).toBeInTheDocument()
  })

  it('renders unauthorized error message', () => {
    render(<ErrorDisplay errorType="unauthorized" />)
    expect(screen.getByText('未授权访问')).toBeInTheDocument()
  })

  it('renders forbidden error message', () => {
    render(<ErrorDisplay errorType="forbidden" />)
    expect(screen.getByText('访问被拒绝')).toBeInTheDocument()
  })

  it('renders validation error message', () => {
    render(<ErrorDisplay errorType="validation" />)
    expect(screen.getByText('请求参数错误')).toBeInTheDocument()
  })

  it('renders rate-limit error message', () => {
    render(<ErrorDisplay errorType="rate-limit" />)
    expect(screen.getByText('请求过于频繁')).toBeInTheDocument()
  })

  it('renders conflict error message', () => {
    render(<ErrorDisplay errorType="conflict" />)
    expect(screen.getByText('数据冲突')).toBeInTheDocument()
  })

  it('renders unknown error message', () => {
    render(<ErrorDisplay errorType="unknown" />)
    expect(screen.getByText('未知错误')).toBeInTheDocument()
  })

  it('renders custom title when provided', () => {
    render(<ErrorDisplay errorType="network" title="自定义标题" />)
    expect(screen.getByText('自定义标题')).toBeInTheDocument()
  })

  it('renders custom description when provided', () => {
    render(<ErrorDisplay errorType="network" description="自定义描述" />)
    expect(screen.getByText('自定义描述')).toBeInTheDocument()
  })

  it('renders retry button for retryable errors', () => {
    render(<ErrorDisplay errorType="network" onRetry={() => {}} />)
    expect(screen.getByText('重试')).toBeInTheDocument()
  })

  it('does not render retry button for non-retryable errors', () => {
    render(<ErrorDisplay errorType="not-found" onRetry={() => {}} />)
    expect(screen.queryByText('重试')).not.toBeInTheDocument()
  })

  it('does not render retry button when onRetry is not provided', () => {
    render(<ErrorDisplay errorType="network" />)
    expect(screen.queryByText('重试')).not.toBeInTheDocument()
  })

  it('calls onRetry when retry button is clicked', async () => {
    const handleRetry = vi.fn()
    const user = userEvent.setup()
    render(<ErrorDisplay errorType="network" onRetry={handleRetry} />)
    await user.click(screen.getByText('重试'))
    expect(handleRetry).toHaveBeenCalledTimes(1)
  })

  it('renders suggestion text', () => {
    render(<ErrorDisplay errorType="network" />)
    expect(screen.getByText(/请检查网络连接后重试/)).toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(
      <ErrorDisplay errorType="network" className="custom-class" />
    )
    expect(container.firstChild).toHaveClass('custom-class')
  })
})
