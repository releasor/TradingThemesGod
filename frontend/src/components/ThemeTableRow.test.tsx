/** ThemeTableRow 组件测试 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ThemeTableRow } from './ThemeTableRow'
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

const negativeTheme: ThemeBrief = {
  ...mockTheme,
  id: 2,
  name: '新能源汽车',
  heat_index: 45.20,
  rise_fall_pct: -1.80,
  stock_count: 30,
  category: '汽车',
}

const zeroRiseFallTheme: ThemeBrief = {
  ...mockTheme,
  id: 3,
  name: '区块链',
  heat_index: 30.00,
  rise_fall_pct: 0,
  stock_count: 15,
  category: null,
}

describe('ThemeTableRow', () => {
  it('renders theme name', () => {
    render(<ThemeTableRow theme={mockTheme} />)
    expect(screen.getByText('人工智能')).toBeInTheDocument()
  })

  it('renders category when present', () => {
    render(<ThemeTableRow theme={mockTheme} />)
    expect(screen.getByText('科技')).toBeInTheDocument()
  })

  it('does not render category when null', () => {
    render(<ThemeTableRow theme={zeroRiseFallTheme} />)
    expect(screen.getByText('区块链')).toBeInTheDocument()
    const badges = screen.queryAllByText('科技')
    expect(badges).toHaveLength(0)
  })

  it('renders heat index value', () => {
    render(<ThemeTableRow theme={mockTheme} />)
    expect(screen.getByText(/热度 95\.5/)).toBeInTheDocument()
  })

  it('renders stock count', () => {
    render(<ThemeTableRow theme={mockTheme} />)
    expect(screen.getByText(/50 只/)).toBeInTheDocument()
  })

  it('renders positive rise fall with + sign', () => {
    render(<ThemeTableRow theme={mockTheme} />)
    expect(screen.getByText('+2.35%')).toBeInTheDocument()
  })

  it('renders negative rise fall without + sign', () => {
    render(<ThemeTableRow theme={negativeTheme} />)
    expect(screen.getByText('-1.80%')).toBeInTheDocument()
  })

  it('renders zero rise fall', () => {
    render(<ThemeTableRow theme={zeroRiseFallTheme} />)
    expect(screen.getByText('0.00%')).toBeInTheDocument()
  })

  it('calls onClick when clicked', async () => {
    const handleClick = vi.fn()
    const user = userEvent.setup()
    render(<ThemeTableRow theme={mockTheme} onClick={handleClick} />)
    await user.click(screen.getByRole('button'))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('renders as a button for accessibility', () => {
    render(<ThemeTableRow theme={mockTheme} />)
    expect(screen.getByRole('button')).toBeInTheDocument()
  })

  it('has correct aria-label', () => {
    render(<ThemeTableRow theme={mockTheme} />)
    expect(screen.getByLabelText('查看题材详情: 人工智能')).toBeInTheDocument()
  })

  it('applies high heat color for heat >= 80', () => {
    render(<ThemeTableRow theme={mockTheme} />)
    const heatBadge = screen.getByText(/热度 95\.5/)
    expect(heatBadge.className).toMatch(/red/)
  })

  it('applies medium heat color for heat 60-80', () => {
    const mediumTheme = { ...mockTheme, heat_index: 70 }
    render(<ThemeTableRow theme={mediumTheme} />)
    const heatBadge = screen.getByText(/热度 70\.0/)
    expect(heatBadge.className).toMatch(/orange/)
  })

  it('applies low heat color for heat 40-60', () => {
    render(<ThemeTableRow theme={negativeTheme} />)
    const heatBadge = screen.getByText(/热度 45\.2/)
    expect(heatBadge.className).toMatch(/yellow/)
  })

  it('applies very low heat color for heat < 40', () => {
    render(<ThemeTableRow theme={zeroRiseFallTheme} />)
    const heatBadge = screen.getByText(/热度 30\.0/)
    expect(heatBadge.className).toMatch(/green/)
  })

  it('applies red color for positive rise fall (Chinese convention)', () => {
    render(<ThemeTableRow theme={mockTheme} />)
    const riseFall = screen.getByText('+2.35%')
    expect(riseFall.className).toMatch(/red/)
  })

  it('applies green color for negative rise fall', () => {
    render(<ThemeTableRow theme={negativeTheme} />)
    const riseFall = screen.getByText('-1.80%')
    expect(riseFall.className).toMatch(/green/)
  })

  it('applies pressed state on mouse down', () => {
    render(<ThemeTableRow theme={mockTheme} />)
    const button = screen.getByRole('button')
    fireEvent.mouseDown(button)
    expect(button.className).toMatch(/scale-\[0\.99\]/)
  })

  it('releases pressed state on mouse up', () => {
    render(<ThemeTableRow theme={mockTheme} />)
    const button = screen.getByRole('button')
    fireEvent.mouseDown(button)
    fireEvent.mouseUp(button)
    // After mouseUp, isPressed becomes false, so the state-dependent class is removed.
    // The "active:" pseudo-class variants are always present (CSS handles them).
    // Check that the standalone "scale-[0.99]" (not preceded by "active:") is absent.
    expect(button.className).not.toMatch(/(?<!active:)scale-\[0\.99\]/)
  })

  it('releases pressed state on mouse leave', () => {
    render(<ThemeTableRow theme={mockTheme} />)
    const button = screen.getByRole('button')
    fireEvent.mouseDown(button)
    fireEvent.mouseLeave(button)
    expect(button.className).not.toMatch(/(?<!active:)scale-\[0\.99\]/)
  })
})
