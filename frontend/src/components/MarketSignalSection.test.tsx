import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { ThemeBrief } from '@/types/theme'
import { MarketSignalSection } from './MarketSignalSection'

vi.mock('@/components/charts/ThemeRiseFallBar', () => ({
  ThemeRiseFallBar: ({
    themes,
    onThemeClick,
  }: {
    themes: ThemeBrief[]
    onThemeClick?: (themeId: number) => void
  }) => (
    <div data-testid="market-signal-ranking">
      {themes.map((theme) => (
        <button key={theme.id} type="button" onClick={() => onThemeClick?.(theme.id)}>
          {theme.name}
        </button>
      ))}
    </div>
  ),
}))

const signals: ThemeBrief[] = [
  {
    id: 81,
    name: '昨日涨停',
    code: 'BK0815',
    description: null,
    heat_index: 80,
    rise_fall_pct: 2.35,
    stock_count: 46,
    category: null,
    tags: null,
    source: 'eastmoney',
  },
  {
    id: 82,
    name: '昨日炸板',
    code: 'BK1631',
    description: null,
    heat_index: 70,
    rise_fall_pct: -1.2,
    stock_count: 18,
    category: null,
    tags: null,
    source: 'eastmoney',
  },
]

describe('MarketSignalSection', () => {
  it('renders market signals as a rise/fall ranking and handles selection', () => {
    const onSelect = vi.fn()
    render(<MarketSignalSection signals={signals} onSelect={onSelect} />)

    expect(screen.getByRole('heading', { name: '市场表现' })).toBeInTheDocument()
    expect(screen.getByTestId('market-signal-ranking')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /昨日涨停/ }))
    expect(onSelect).toHaveBeenCalledWith(81)
  })

  it('renders stable loading placeholders', () => {
    render(<MarketSignalSection signals={[]} isLoading onSelect={vi.fn()} />)
    expect(screen.getByTestId('market-signal-skeleton')).toHaveClass('h-[380px]')
  })

  it('renders an empty message', () => {
    render(<MarketSignalSection signals={[]} onSelect={vi.fn()} />)
    expect(screen.getByText('暂无市场表现数据')).toBeInTheDocument()
  })

  it('renders a local error without throwing', () => {
    render(<MarketSignalSection signals={[]} isError onSelect={vi.fn()} />)
    expect(screen.getByText('市场表现加载失败')).toBeInTheDocument()
  })

  it('supports custom title for indicator ranking column', () => {
    render(
      <MarketSignalSection
        title="行情指标"
        headingId="indicator-signal-heading"
        emptyText="暂无行情指标数据"
        signals={[]}
        onSelect={vi.fn()}
      />
    )
    expect(screen.getByRole('heading', { name: '行情指标' })).toBeInTheDocument()
    expect(screen.getByText('暂无行情指标数据')).toBeInTheDocument()
  })
})
