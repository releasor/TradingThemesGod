import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { MarketStrategyCard } from './MarketStrategyCard'

describe('MarketStrategyCard', () => {
  it('renders the optimized index and emotion strategy', () => {
    render(
      <MarketStrategyCard
        card={{
          title: '指数情绪策略卡',
          index_strength: 'strong',
          emotion_strength: 'weak',
          primary_strategy: '补涨趋势与切换',
          secondary_strategy: '轮动低吸',
          operation_advice: '指数强但情绪弱，做补涨、趋势和高低切换。',
          focus_targets: ['低位补涨', '趋势承接'],
          rationale: ['指数强度 0.80', '情绪强度 32，日均连板 6.0'],
        }}
        period="today"
        periodLabel="当日"
        dateRange="2026-07-21"
      />
    )

    expect(screen.getByText('指数情绪策略卡')).toBeInTheDocument()
    expect(screen.getByText('当日')).toBeInTheDocument()
    expect(screen.getByText(/2026-07-21/)).toBeInTheDocument()
    expect(screen.getByText('补涨趋势与切换')).toBeInTheDocument()
    expect(screen.getByText('轮动低吸')).toBeInTheDocument()
    expect(screen.getByText(/做补涨/)).toBeInTheDocument()
  })

  it('switches between preset and custom periods', async () => {
    const onPeriodChange = vi.fn()
    const user = userEvent.setup()

    render(
      <MarketStrategyCard
        card={{
          title: '指数情绪策略卡',
          index_strength: 'strong',
          emotion_strength: 'strong',
          primary_strategy: '连板接力',
          secondary_strategy: '主升分歧接力',
          operation_advice: '指数强、情绪强，做连板。',
          focus_targets: ['连板梯队'],
          rationale: ['日均连板 28.0'],
        }}
        period="today"
        periodLabel="当日"
        onPeriodChange={onPeriodChange}
      />
    )

    expect(screen.getByRole('button', { name: '当日' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: '本周' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '近半月' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '本月' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '自定义' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '本周' }))

    expect(onPeriodChange).toHaveBeenCalledWith('current_week')
  })

  it('shows custom date inputs and emits date range changes', async () => {
    const onPeriodChange = vi.fn()
    const onCustomDateRangeChange = vi.fn()

    render(
      <MarketStrategyCard
        card={{
          title: '指数情绪策略卡',
          index_strength: 'strong',
          emotion_strength: 'weak',
          primary_strategy: '补涨趋势与切换',
          secondary_strategy: '轮动低吸',
          operation_advice: '指数强但情绪弱，做补涨、趋势和高低切换。',
          focus_targets: ['低位补涨'],
          rationale: ['日均连板 3.5'],
        }}
        period="custom"
        periodLabel="自定义"
        customStartDate="2026-07-03"
        customEndDate="2026-07-17"
        onPeriodChange={onPeriodChange}
        onCustomDateRangeChange={onCustomDateRangeChange}
      />
    )

    expect(screen.getByLabelText('自定义开始日期')).toHaveValue('2026-07-03')
    expect(screen.getByLabelText('自定义结束日期')).toHaveValue('2026-07-17')

    fireEvent.change(screen.getByLabelText('自定义开始日期'), {
      target: { value: '2026-07-06' },
    })

    expect(onCustomDateRangeChange).toHaveBeenLastCalledWith('2026-07-06', '2026-07-17')
    expect(onPeriodChange).not.toHaveBeenCalled()
  })

  it('shows refresh and database analyze actions', async () => {
    const onRefreshData = vi.fn()
    const onAnalyzeDatabase = vi.fn()
    const user = userEvent.setup()

    render(
      <MarketStrategyCard
        card={{
          title: '指数情绪策略卡',
          index_strength: 'strong',
          emotion_strength: 'weak',
          primary_strategy: '补涨趋势与切换',
          secondary_strategy: '轮动低吸',
          operation_advice: '指数强但情绪弱，做补涨、趋势和高低切换。',
          focus_targets: ['低位补涨'],
          rationale: ['指数强度 0.39'],
        }}
        period="today"
        periodLabel="当日"
        onRefreshData={onRefreshData}
        onAnalyzeDatabase={onAnalyzeDatabase}
      />
    )

    await user.click(screen.getByRole('button', { name: '刷新行情' }))
    await user.click(screen.getByRole('button', { name: '数据库分析' }))

    expect(onRefreshData).toHaveBeenCalledTimes(1)
    expect(onAnalyzeDatabase).toHaveBeenCalledTimes(1)
  })

  it('shows period refresh progress and result inside the card', () => {
    const { rerender } = render(
      <MarketStrategyCard
        card={{
          title: '指数情绪策略卡',
          index_strength: 'strong',
          emotion_strength: 'strong',
          primary_strategy: '连板接力',
          secondary_strategy: '主升分歧接力',
          operation_advice: '指数强、情绪强，做连板。',
          focus_targets: ['连板梯队'],
          rationale: ['日均连板 28.0'],
        }}
        period="current_month"
        periodLabel="本月"
        periodStatus={{ type: 'progress', message: '正在刷新本月策略数据...' }}
      />
    )

    expect(screen.getByText('正在刷新本月策略数据...')).toBeInTheDocument()

    rerender(
      <MarketStrategyCard
        card={{
          title: '指数情绪策略卡',
          index_strength: 'strong',
          emotion_strength: 'weak',
          primary_strategy: '补涨趋势与切换',
          secondary_strategy: '轮动低吸',
          operation_advice: '指数强但情绪弱，做补涨、趋势和高低切换。',
          focus_targets: ['低位补涨'],
          rationale: ['周期市场快照已聚合'],
        }}
        period="current_month"
        periodLabel="本月"
        periodStatus={{ type: 'success', message: '本月策略数据已刷新' }}
      />
    )

    expect(screen.getByText('本月策略数据已刷新')).toBeInTheDocument()
  })
})
