/** ThemeCard 组件测试 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ThemeCard } from './ThemeCard'
import type { ThemeBrief } from '@/types/theme'

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

describe('ThemeCard', () => {
  it('renders theme name', () => {
    render(<ThemeCard theme={mockTheme} />)

    expect(screen.getByText('人工智能')).toBeInTheDocument()
  })

  it('renders heat index', () => {
    render(<ThemeCard theme={mockTheme} />)

    expect(screen.getByText(/热度 95.5/)).toBeInTheDocument()
  })

  it('renders stock count', () => {
    render(<ThemeCard theme={mockTheme} />)

    expect(screen.getByText(/50 只/)).toBeInTheDocument()
  })

  it('renders positive rise fall percentage with + sign', () => {
    render(<ThemeCard theme={mockTheme} />)

    expect(screen.getByText('+2.35%')).toBeInTheDocument()
  })

  it('renders negative rise fall percentage without + sign', () => {
    const negativeTheme = { ...mockTheme, rise_fall_pct: -1.50 }
    render(<ThemeCard theme={negativeTheme} />)

    expect(screen.getByText('-1.50%')).toBeInTheDocument()
  })

  it('calls onClick when clicked', async () => {
    const handleClick = vi.fn()
    const user = userEvent.setup()

    render(<ThemeCard theme={mockTheme} onClick={handleClick} />)

    await user.click(screen.getByText('人工智能'))

    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('renders as a button for accessibility', () => {
    render(<ThemeCard theme={mockTheme} />)

    const button = screen.getByRole('button')
    expect(button).toBeInTheDocument()
  })

  it('applies heat color class based on heat index', () => {
    render(<ThemeCard theme={mockTheme} />)

    const heatBadge = screen.getByText(/热度 95.5/)
    // High heat should have red/warm color
    expect(heatBadge.className).toMatch(/red|orange/)
  })

  it('applies rise fall color class', () => {
    render(<ThemeCard theme={mockTheme} />)

    const riseFallText = screen.getByText('+2.35%')
    // Positive should have green color
    expect(riseFallText.className).toMatch(/green/)
  })
})
