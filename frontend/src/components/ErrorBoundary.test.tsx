/** ErrorBoundary 组件测试 */

import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ErrorBoundary } from './ErrorBoundary'

// 构造一个会抛出错误的组件
function ThrowingComponent({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error('测试错误信息')
  }
  return <div>正常内容</div>
}

describe('ErrorBoundary', () => {
  // 抑制 React 的控制台错误输出
  let consoleErrorSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    consoleErrorSpy.mockRestore()
  })

  it('无错误时正常渲染子组件', () => {
    render(
      <ErrorBoundary>
        <div>子组件内容</div>
      </ErrorBoundary>
    )
    expect(screen.getByText('子组件内容')).toBeInTheDocument()
  })

  it('子组件抛出错误时显示错误 UI', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    )
    expect(screen.getByText('页面出错了')).toBeInTheDocument()
    expect(screen.getByText(/抱歉，页面渲染时发生了错误/)).toBeInTheDocument()
  })

  it('错误详情中显示错误信息', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    )
    expect(screen.getByText('错误详情')).toBeInTheDocument()
    expect(screen.getByText('测试错误信息')).toBeInTheDocument()
  })

  it('重试按钮清除错误状态并重新渲染子组件', () => {
    const { rerender } = render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    )

    expect(screen.getByText('页面出错了')).toBeInTheDocument()

    // 先更新子组件使其不再抛错
    rerender(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={false} />
      </ErrorBoundary>
    )

    // 再点击重试按钮清除错误状态
    fireEvent.click(screen.getByText('重试'))

    expect(screen.getByText('正常内容')).toBeInTheDocument()
    expect(screen.queryByText('页面出错了')).not.toBeInTheDocument()
  })

  it('刷新页面按钮存在', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    )
    expect(screen.getByText('刷新页面')).toBeInTheDocument()
  })

  it('点击刷新页面按钮调用 window.location.reload', () => {
    const reloadSpy = vi.fn()
    vi.stubGlobal('location', { ...window.location, reload: reloadSpy })

    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    )

    fireEvent.click(screen.getByText('刷新页面'))
    expect(reloadSpy).toHaveBeenCalled()

    vi.unstubAllGlobals()
  })
})
