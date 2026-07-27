/** ThemeCard 组件测试 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeCard } from './ThemeCard'
import type { ThemeBrief } from '@/types/theme'
import type { ReactElement } from 'react'

const mockTheme: ThemeBrief = {
  id: 1,
  name: '人工智能',
  code: 'AI',
  description: 'AI 相关题材',
  heat_index: 95.50,
  rise_fall_pct: 2.35,
  stock_count: 50,
  category: '科技',
  tags: ['AI', '机器学习'],
  source: '东方财富',
}

function renderWithClient(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

describe('ThemeCard', () => {
  it('renders theme name', () => {
    renderWithClient(<ThemeCard theme={mockTheme} />)

    expect(screen.getByText('人工智能')).toBeInTheDocument()
  })

  it('renders heat index', () => {
    renderWithClient(<ThemeCard theme={mockTheme} />)

    expect(screen.getByText(/热度 95.5/)).toBeInTheDocument()
  })

  it('renders stock count', () => {
    renderWithClient(<ThemeCard theme={mockTheme} />)

    expect(screen.getByText(/50 只/)).toBeInTheDocument()
  })

  it('renders positive rise fall percentage with + sign', () => {
    renderWithClient(<ThemeCard theme={mockTheme} />)

    expect(screen.getByText('+2.35%')).toBeInTheDocument()
  })

  it('renders negative rise fall percentage without + sign', () => {
    const negativeTheme = { ...mockTheme, rise_fall_pct: -1.50 }
    renderWithClient(<ThemeCard theme={negativeTheme} />)

    expect(screen.getByText('-1.50%')).toBeInTheDocument()
  })

  it('calls onClick when clicked', async () => {
    const handleClick = vi.fn()
    const user = userEvent.setup()

    renderWithClient(<ThemeCard theme={mockTheme} onClick={handleClick} />)

    await user.click(screen.getByText('人工智能'))

    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('renders as a button for accessibility', () => {
    renderWithClient(<ThemeCard theme={mockTheme} />)

    const button = screen.getByRole('button')
    expect(button).toBeInTheDocument()
  })

  it('applies heat color class based on heat index', () => {
    renderWithClient(<ThemeCard theme={mockTheme} />)

    const heatBadge = screen.getByText(/热度 95.5/)
    // High heat should have red/warm color
    expect(heatBadge.className).toMatch(/red|orange/)
  })

  it('applies rise fall color class', () => {
    renderWithClient(<ThemeCard theme={mockTheme} />)

    const riseFallText = screen.getByText('+2.35%')
    // A 股习惯：上涨为红色
    expect(riseFallText.className).toMatch(/red/)
  })
})
