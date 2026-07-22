/** Toast 组件测试 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import { ToastContainer, useToast, type Toast } from './Toast'

describe('ToastContainer', () => {
  const mockOnClose = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders nothing when no toasts', () => {
    const { container } = render(<ToastContainer toasts={[]} onClose={mockOnClose} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders success toast', () => {
    const toasts: Toast[] = [
      { id: '1', type: 'success', message: '操作成功', duration: 4000 },
    ]
    render(<ToastContainer toasts={toasts} onClose={mockOnClose} />)
    expect(screen.getByText('操作成功')).toBeInTheDocument()
  })

  it('renders error toast', () => {
    const toasts: Toast[] = [
      { id: '1', type: 'error', message: '操作失败', duration: 4000 },
    ]
    render(<ToastContainer toasts={toasts} onClose={mockOnClose} />)
    expect(screen.getByText('操作失败')).toBeInTheDocument()
  })

  it('renders warning toast', () => {
    const toasts: Toast[] = [
      { id: '1', type: 'warning', message: '警告信息', duration: 4000 },
    ]
    render(<ToastContainer toasts={toasts} onClose={mockOnClose} />)
    expect(screen.getByText('警告信息')).toBeInTheDocument()
  })

  it('renders info toast', () => {
    const toasts: Toast[] = [
      { id: '1', type: 'info', message: '提示信息', duration: 4000 },
    ]
    render(<ToastContainer toasts={toasts} onClose={mockOnClose} />)
    expect(screen.getByText('提示信息')).toBeInTheDocument()
  })

  it('renders multiple toasts', () => {
    const toasts: Toast[] = [
      { id: '1', type: 'success', message: '成功1', duration: 4000 },
      { id: '2', type: 'error', message: '失败1', duration: 4000 },
    ]
    render(<ToastContainer toasts={toasts} onClose={mockOnClose} />)
    expect(screen.getByText('成功1')).toBeInTheDocument()
    expect(screen.getByText('失败1')).toBeInTheDocument()
  })

  it('calls onClose when close button is clicked', () => {
    const toasts: Toast[] = [
      { id: '1', type: 'success', message: '操作成功', duration: 4000 },
    ]
    render(<ToastContainer toasts={toasts} onClose={mockOnClose} />)
    fireEvent.click(screen.getByLabelText('关闭通知'))
    expect(mockOnClose).toHaveBeenCalledWith('1')
  })

  it('auto-closes after duration', () => {
    const toasts: Toast[] = [
      { id: '1', type: 'success', message: '操作成功', duration: 3000 },
    ]
    render(<ToastContainer toasts={toasts} onClose={mockOnClose} />)
    act(() => {
      vi.advanceTimersByTime(3000)
    })
    expect(mockOnClose).toHaveBeenCalledWith('1')
  })

  it('has correct accessibility attributes', () => {
    const toasts: Toast[] = [
      { id: '1', type: 'success', message: '操作成功', duration: 4000 },
    ]
    render(<ToastContainer toasts={toasts} onClose={mockOnClose} />)
    const container = screen.getByRole('status')
    expect(container).toHaveAttribute('aria-live', 'polite')
  })
})

describe('useToast hook', () => {
  function TestComponent() {
    const { toasts, addToast, removeToast, success, error, warning, info } = useToast()

    return (
      <div>
        <span data-testid="count">{toasts.length}</span>
        <button onClick={() => success('成功')}>success</button>
        <button onClick={() => error('失败')}>error</button>
        <button onClick={() => warning('警告')}>warning</button>
        <button onClick={() => info('提示')}>info</button>
        <button onClick={() => addToast('success', '自定义', 5000)}>add</button>
        {toasts.length > 0 && (
          <button onClick={() => removeToast(toasts[0].id)}>remove</button>
        )}
      </div>
    )
  }

  it('starts with empty toasts', () => {
    render(<TestComponent />)
    expect(screen.getByTestId('count').textContent).toBe('0')
  })

  it('adds success toast', async () => {
    const user = (await import('@testing-library/user-event')).default.setup()
    render(<TestComponent />)
    await user.click(screen.getByText('success'))
    expect(screen.getByTestId('count').textContent).toBe('1')
  })

  it('adds error toast', async () => {
    const user = (await import('@testing-library/user-event')).default.setup()
    render(<TestComponent />)
    await user.click(screen.getByText('error'))
    expect(screen.getByTestId('count').textContent).toBe('1')
  })

  it('adds warning toast', async () => {
    const user = (await import('@testing-library/user-event')).default.setup()
    render(<TestComponent />)
    await user.click(screen.getByText('warning'))
    expect(screen.getByTestId('count').textContent).toBe('1')
  })

  it('adds info toast', async () => {
    const user = (await import('@testing-library/user-event')).default.setup()
    render(<TestComponent />)
    await user.click(screen.getByText('info'))
    expect(screen.getByTestId('count').textContent).toBe('1')
  })

  it('adds toast with custom duration', async () => {
    const user = (await import('@testing-library/user-event')).default.setup()
    render(<TestComponent />)
    await user.click(screen.getByText('add'))
    expect(screen.getByTestId('count').textContent).toBe('1')
  })

  it('removes toast by id', async () => {
    const user = (await import('@testing-library/user-event')).default.setup()
    render(<TestComponent />)
    await user.click(screen.getByText('success'))
    expect(screen.getByTestId('count').textContent).toBe('1')
    await user.click(screen.getByText('remove'))
    expect(screen.getByTestId('count').textContent).toBe('0')
  })

  it('adds multiple toasts', async () => {
    const user = (await import('@testing-library/user-event')).default.setup()
    render(<TestComponent />)
    await user.click(screen.getByText('success'))
    await user.click(screen.getByText('error'))
    await user.click(screen.getByText('warning'))
    expect(screen.getByTestId('count').textContent).toBe('3')
  })
})
