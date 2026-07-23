/** AutoRefreshButton 组件测试 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AutoRefreshButton } from './AutoRefreshButton'

describe('AutoRefreshButton', () => {
  const defaultProps = {
    isAutoRefresh: false,
    onToggleAutoRefresh: vi.fn(),
    refreshInterval: 30000,
    onSetRefreshInterval: vi.fn(),
    onRefresh: vi.fn(),
    onFullUpdate: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders light refresh and full update buttons', () => {
    render(<AutoRefreshButton {...defaultProps} />)
    expect(screen.getByRole('button', { name: '刷新' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '全量更新' })).toBeInTheDocument()
  })

  it('hides full update button when onFullUpdate is omitted', () => {
    const { onFullUpdate: _ignored, ...props } = defaultProps
    render(<AutoRefreshButton {...props} />)
    expect(screen.getByRole('button', { name: '刷新' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '全量更新' })).not.toBeInTheDocument()
  })

  it('renders auto refresh toggle button', () => {
    render(<AutoRefreshButton {...defaultProps} />)
    expect(screen.getByText('自动刷新')).toBeInTheDocument()
  })

  it('calls onRefresh when light refresh button is clicked', () => {
    render(<AutoRefreshButton {...defaultProps} />)
    fireEvent.click(screen.getByRole('button', { name: '刷新' }))
    expect(defaultProps.onRefresh).toHaveBeenCalledTimes(1)
    expect(defaultProps.onFullUpdate).not.toHaveBeenCalled()
  })

  it('calls onFullUpdate when full update button is clicked', () => {
    render(<AutoRefreshButton {...defaultProps} />)
    fireEvent.click(screen.getByRole('button', { name: '全量更新' }))
    expect(defaultProps.onFullUpdate).toHaveBeenCalledTimes(1)
    expect(defaultProps.onRefresh).not.toHaveBeenCalled()
  })

  it('calls onToggleAutoRefresh when auto refresh button is clicked', () => {
    render(<AutoRefreshButton {...defaultProps} />)
    fireEvent.click(screen.getByText('自动刷新'))
    expect(defaultProps.onToggleAutoRefresh).toHaveBeenCalledTimes(1)
  })

  it('shows play icon when auto refresh is off', () => {
    render(<AutoRefreshButton {...defaultProps} isAutoRefresh={false} />)
    const toggleBtn = screen.getByText('自动刷新').closest('button')!
    expect(toggleBtn.title).toBe('开启自动刷新')
  })

  it('shows pause icon when auto refresh is on', () => {
    render(<AutoRefreshButton {...defaultProps} isAutoRefresh={true} />)
    const toggleBtn = screen.getByText('自动刷新').closest('button')!
    expect(toggleBtn.title).toBe('停止自动刷新')
  })

  it('shows interval selector when auto refresh is on', () => {
    render(<AutoRefreshButton {...defaultProps} isAutoRefresh={true} />)
    expect(screen.getByRole('combobox')).toBeInTheDocument()
  })

  it('hides interval selector when auto refresh is off', () => {
    render(<AutoRefreshButton {...defaultProps} isAutoRefresh={false} />)
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
  })

  it('displays interval options when auto refresh is on', () => {
    render(<AutoRefreshButton {...defaultProps} isAutoRefresh={true} />)
    const select = screen.getByRole('combobox')
    expect(select).toBeInTheDocument()
    expect(screen.getByText('10 秒')).toBeInTheDocument()
    expect(screen.getByText('30 秒')).toBeInTheDocument()
    expect(screen.getByText('1 分钟')).toBeInTheDocument()
    expect(screen.getByText('5 分钟')).toBeInTheDocument()
  })

  it('calls onSetRefreshInterval when interval is changed', () => {
    render(<AutoRefreshButton {...defaultProps} isAutoRefresh={true} />)
    const select = screen.getByRole('combobox')
    fireEvent.change(select, { target: { value: '60000' } })
    expect(defaultProps.onSetRefreshInterval).toHaveBeenCalledWith(60000)
  })

  it('disables both action buttons when refreshing or updating', () => {
    const { rerender } = render(<AutoRefreshButton {...defaultProps} isRefreshing />)
    expect(screen.getByRole('button', { name: '刷新' })).toBeDisabled()
    expect(screen.getByRole('button', { name: '全量更新' })).toBeDisabled()

    rerender(<AutoRefreshButton {...defaultProps} isUpdating />)
    expect(screen.getByRole('button', { name: '刷新' })).toBeDisabled()
    expect(screen.getByRole('button', { name: '全量更新中…' })).toBeDisabled()
  })

  it('enables action buttons when idle', () => {
    render(<AutoRefreshButton {...defaultProps} />)
    expect(screen.getByRole('button', { name: '刷新' })).not.toBeDisabled()
    expect(screen.getByRole('button', { name: '全量更新' })).not.toBeDisabled()
  })

  it('applies custom className', () => {
    const { container } = render(
      <AutoRefreshButton {...defaultProps} className="my-class" />
    )
    expect(container.firstChild).toHaveClass('my-class')
  })

  it('shows source selector when multiple sources are available', () => {
    render(
      <AutoRefreshButton
        {...defaultProps}
        scraperSources={[
          { id: 'eastmoney', label: '东方财富', description: '题材列表' },
          { id: 'akshare', label: 'AKShare', description: 'A 股行情' },
        ]}
        selectedScraperSource="eastmoney"
        onScraperSourceChange={vi.fn()}
      />
    )
    expect(screen.getByLabelText('全量更新数据源')).toBeInTheDocument()
    expect(screen.getByRole('option', { name: '东方财富' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'AKShare' })).toBeInTheDocument()
  })

  it('calls onScraperSourceChange when source is changed', () => {
    const onScraperSourceChange = vi.fn()
    render(
      <AutoRefreshButton
        {...defaultProps}
        scraperSources={[
          { id: 'eastmoney', label: '东方财富', description: '题材列表' },
          { id: 'akshare', label: 'AKShare', description: 'A 股行情' },
        ]}
        selectedScraperSource="eastmoney"
        onScraperSourceChange={onScraperSourceChange}
      />
    )
    fireEvent.change(screen.getByLabelText('全量更新数据源'), { target: { value: 'akshare' } })
    expect(onScraperSourceChange).toHaveBeenCalledWith('akshare')
  })

  it('hides source selector when only one source is available', () => {
    render(
      <AutoRefreshButton
        {...defaultProps}
        scraperSources={[{ id: 'eastmoney', label: '东方财富', description: '题材列表' }]}
        selectedScraperSource="eastmoney"
        onScraperSourceChange={vi.fn()}
      />
    )
    expect(screen.queryByLabelText('全量更新数据源')).not.toBeInTheDocument()
  })

  it('has correct current interval value selected', () => {
    render(
      <AutoRefreshButton {...defaultProps} isAutoRefresh={true} refreshInterval={60000} />
    )
    const select = screen.getByRole('combobox')
    expect(select).toHaveValue('60000')
  })
})
