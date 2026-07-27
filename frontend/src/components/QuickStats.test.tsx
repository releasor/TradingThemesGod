/** QuickStats 组件测试 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QuickStats } from './QuickStats'

describe('QuickStats', () => {
  it('renders theme count', () => {
    render(<QuickStats totalThemes={42} totalStocks={120} lastUpdate="2025-01-01" />)
    expect(screen.getByText('题材总数')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
  })

  it('renders stock count', () => {
    render(<QuickStats totalThemes={42} totalStocks={120} lastUpdate="2025-01-01" />)
    expect(screen.getByText('股票总数')).toBeInTheDocument()
    expect(screen.getByText('120')).toBeInTheDocument()
  })

  it('renders last update time', () => {
    render(<QuickStats totalThemes={42} totalStocks={120} lastUpdate="2025-01-01" />)
    expect(screen.getByText('行情更新')).toBeInTheDocument()
    expect(screen.getByText('2025-01-01')).toBeInTheDocument()
  })

  it('shows fallback text when lastUpdate is null', () => {
    render(<QuickStats totalThemes={0} totalStocks={0} lastUpdate={null} />)
    expect(screen.getByText('暂无数据')).toBeInTheDocument()
  })

  it('renders zero counts', () => {
    render(<QuickStats totalThemes={0} totalStocks={0} lastUpdate="2025-01-01" />)
    const zeroValues = screen.getAllByText('0')
    expect(zeroValues).toHaveLength(2)
  })

  it('renders large numbers', () => {
    render(<QuickStats totalThemes={9999} totalStocks={50000} lastUpdate="2025-06-15" />)
    expect(screen.getByText('9999')).toBeInTheDocument()
    expect(screen.getByText('50000')).toBeInTheDocument()
  })

  it('does not render market clock in stats bar', () => {
    render(<QuickStats totalThemes={1} totalStocks={1} lastUpdate={null} />)
    expect(screen.queryByTestId('market-now')).not.toBeInTheDocument()
    expect(screen.queryByTestId('trading-day-label')).not.toBeInTheDocument()
    expect(screen.queryByTestId('market-session')).not.toBeInTheDocument()
  })
})
