/** 看板刷新进度与当前板块状态 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { DashboardRefreshStatus } from './DashboardRefreshStatus'

describe('DashboardRefreshStatus', () => {
  it('shows current section and progress bar while active', () => {
    render(
      <DashboardRefreshStatus
        active
        progressPct={42}
        pendingLabel="策略卡"
        doneLabels={['题材行情', '热度榜']}
        message="已更新：题材行情；热度榜。正在更新：策略卡（已耗时 12 秒）..."
        messageType="progress"
      />
    )

    expect(screen.getByTestId('dashboard-refresh-status')).toBeInTheDocument()
    expect(screen.getByText('正在更新：策略卡')).toBeInTheDocument()
    expect(screen.getByText('42%')).toBeInTheDocument()
    expect(screen.getByText(/已完成：题材行情；热度榜/)).toBeInTheDocument()
    expect(screen.getByTestId('dashboard-refresh-status-bar')).toHaveStyle({ width: '42%' })
  })

  it('hides when idle and no message', () => {
    const { container } = render(
      <DashboardRefreshStatus
        active={false}
        progressPct={null}
        pendingLabel={null}
        doneLabels={[]}
        message={null}
      />
    )
    expect(container).toBeEmptyDOMElement()
  })
})
