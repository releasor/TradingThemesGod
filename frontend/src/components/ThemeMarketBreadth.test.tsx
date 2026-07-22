import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ThemeMarketBreadth } from './ThemeMarketBreadth'

const snapshot = {
  trade_date: '2026-07-20',
  up_count: 12,
  down_count: 0,
  flat_count: 1,
  suspended_count: 2,
  limit_up_count: null,
  limit_down_count: 0,
  calculated_at: '2026-07-20T15:00:00Z',
  up_down_ratio: null,
  up_down_display: '12:0',
}

describe('ThemeMarketBreadth', () => {
  it('distinguishes unavailable counts from zero', () => {
    render(<ThemeMarketBreadth snapshot={snapshot} />)
    expect(screen.getByTestId('limit-up-count')).toHaveTextContent('暂无数据')
    expect(screen.getByTestId('limit-down-count')).toHaveTextContent('0')
    expect(screen.getByText('12:0')).toBeInTheDocument()
  })
})
