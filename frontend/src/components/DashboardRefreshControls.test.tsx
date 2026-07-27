import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { DashboardRefreshControls } from './DashboardRefreshControls'

describe('DashboardRefreshControls', () => {
  it('shows light/full and cancel when busy', () => {
    const onCancel = vi.fn()
    render(
      <DashboardRefreshControls
        isRefreshing
        isUpdating={false}
        onRefresh={vi.fn()}
        onFullUpdate={vi.fn()}
        onCancel={onCancel}
        refreshElapsedLabel="0:12"
      />
    )
    expect(screen.getByRole('button', { name: /取消/ })).toBeInTheDocument()
    expect(screen.queryByText('自动刷新')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /取消/ }))
    expect(onCancel).toHaveBeenCalled()
  })

  it('hides cancel when idle', () => {
    render(
      <DashboardRefreshControls
        isRefreshing={false}
        isUpdating={false}
        onRefresh={vi.fn()}
        onFullUpdate={vi.fn()}
        onCancel={vi.fn()}
      />
    )
    expect(screen.queryByRole('button', { name: /取消/ })).not.toBeInTheDocument()
  })

  it('calls onRefresh and onFullUpdate when idle', () => {
    const onRefresh = vi.fn()
    const onFullUpdate = vi.fn()
    render(
      <DashboardRefreshControls
        isRefreshing={false}
        isUpdating={false}
        onRefresh={onRefresh}
        onFullUpdate={onFullUpdate}
        onCancel={vi.fn()}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: '刷新' }))
    fireEvent.click(screen.getByRole('button', { name: '全量更新' }))
    expect(onRefresh).toHaveBeenCalledTimes(1)
    expect(onFullUpdate).toHaveBeenCalledTimes(1)
  })

  it('disables light and full buttons when busy', () => {
    render(
      <DashboardRefreshControls
        isRefreshing
        isUpdating={false}
        onRefresh={vi.fn()}
        onFullUpdate={vi.fn()}
        onCancel={vi.fn()}
        refreshElapsedLabel="0:05"
      />
    )
    expect(screen.getByRole('button', { name: /刷新中/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: '全量更新' })).toBeDisabled()
    expect(screen.getByRole('button', { name: /取消/ })).not.toBeDisabled()
  })

  it('shows elapsed labels when refreshing or updating', () => {
    const { rerender } = render(
      <DashboardRefreshControls
        isRefreshing
        isUpdating={false}
        onRefresh={vi.fn()}
        onFullUpdate={vi.fn()}
        onCancel={vi.fn()}
        refreshElapsedLabel="0:12"
      />
    )
    expect(screen.getByRole('button', { name: '刷新中 0:12' })).toBeInTheDocument()

    rerender(
      <DashboardRefreshControls
        isRefreshing={false}
        isUpdating
        onRefresh={vi.fn()}
        onFullUpdate={vi.fn()}
        onCancel={vi.fn()}
        updateElapsedLabel="1:30"
      />
    )
    expect(screen.getByRole('button', { name: '全量更新中 1:30' })).toBeInTheDocument()
  })
})
