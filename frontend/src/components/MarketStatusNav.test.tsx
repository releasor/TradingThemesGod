/** MarketStatusNav 组件测试 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MarketStatusNav } from './MarketStatusNav'
import { setMarketCalendarOverride } from '@/lib/marketClock'

vi.mock('@/api/trading-calendar', () => ({
  fetchCalendarStatus: vi.fn(async () => {
    throw new Error('offline')
  }),
}))

function renderNav() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MarketStatusNav />
    </QueryClientProvider>
  )
}

describe('MarketStatusNav', () => {
  beforeEach(() => {
    setMarketCalendarOverride(null)
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-07-25T03:00:00Z')) // 周六 11:00 上海
  })

  afterEach(() => {
    setMarketCalendarOverride(null)
    vi.useRealTimers()
  })

  it('renders weekend market status', () => {
    renderNav()
    expect(screen.getByTestId('trading-day-label')).toHaveTextContent('非交易日')
    expect(screen.getByTestId('market-session')).toHaveTextContent('休市（周末）')
    expect(screen.getByTestId('market-now')).toHaveTextContent('2026-07-25')
  })

  it('renders three separate rows inside a translucent card', () => {
    renderNav()
    const root = screen.getByTestId('market-status-nav')
    expect(root).toHaveClass('flex-col')
    expect(root).toHaveClass('backdrop-blur-sm')
    expect(root).toHaveClass('bg-background/70')
    expect(root.children).toHaveLength(3)
  })
})
