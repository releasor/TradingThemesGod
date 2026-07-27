/** 一进二打板参考卡测试 */

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { BoardUpgradeReference } from './BoardUpgradeReference'

describe('BoardUpgradeReference', () => {
  const response = {
    trade_date: '2026-07-21',
    previous_trade_date: '2026-07-20',
    refreshed_at: '2026-07-21T10:30:00Z',
    degraded: true,
    missing_sources: ['model_catalyst'],
    candidates: [
      {
        code: '000001',
        name: '平安银行',
        theme_name: '金融科技',
        price: 12.3,
        market_cap: 120,
        float_market_cap: 60,
        turnover_rate: 8.5,
        amount: 9.2,
        first_limit_up_at: '09:42:00',
        open_board_count: 0,
        score: 86,
        decision: 'candidate' as const,
        matched_rules: ['今日仍在涨停池', '流通市值 20-80 亿'],
        excluded_rules: [],
        risk_flags: ['模型催化缺失'],
        catalysts: ['行业催化：金融科技'],
        operation_advice: '只做换手晋级确认。',
        core_conclusion: '具备一进二观察价值。',
      },
    ],
    excluded_count: 2,
    source_status: { limit_pool: 'success' },
  }

  it('renders live candidates instead of a static checklist', () => {
    render(<BoardUpgradeReference data={response} isLoading={false} />)

    expect(screen.getByRole('heading', { name: '一进二打板参考' })).toBeInTheDocument()
    expect(screen.getByText('平安银行')).toBeInTheDocument()
    expect(screen.getByText('000001')).toBeInTheDocument()
    expect(screen.getByText('86')).toBeInTheDocument()
    expect(screen.getByText('今日仍在涨停池')).toBeInTheDocument()
    expect(screen.getByText('模型催化缺失')).toBeInTheDocument()
    expect(screen.getByText(/数据降级/)).toBeInTheDocument()
    expect(screen.queryByText('参考首板 · 一进二')).not.toBeInTheDocument()
  })

  it('calls refresh when the realtime refresh button is clicked', async () => {
    const onRefresh = vi.fn()
    const user = userEvent.setup()

    render(<BoardUpgradeReference data={response} isLoading={false} onRefresh={onRefresh} />)

    await user.click(screen.getByRole('button', { name: '实时刷新' }))

    expect(onRefresh).toHaveBeenCalledTimes(1)
  })

  it('shows an empty state when no candidates are available', () => {
    render(
      <BoardUpgradeReference
        data={{ ...response, candidates: [], excluded_count: 3, degraded: false }}
        isLoading={false}
      />
    )

    expect(screen.getByText('暂无符合条件的一进二候选')).toBeInTheDocument()
  })

  it('renders candidates in an animated scroll list like news cards', () => {
    render(<BoardUpgradeReference data={response} isLoading={false} />)

    expect(screen.getByTestId('board-upgrade-scroll-container')).toBeInTheDocument()
    expect(screen.getByTestId('board-upgrade-item-000001')).toBeInTheDocument()
  })
})
