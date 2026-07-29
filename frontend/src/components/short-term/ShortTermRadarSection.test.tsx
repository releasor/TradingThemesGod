/** ShortTermRadarSection：轮动列使用 AnimatedList（与实时资讯同款下拉动效） */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { ShortTermRadarSection } from './ShortTermRadarSection'

vi.mock('@/api/short-term', () => ({
  fetchShortTermSectors: vi.fn(),
  refreshShortTermSignals: vi.fn(),
}))

vi.mock('motion/react', () => ({
  motion: {
    div: ({
      children,
      ...props
    }: React.PropsWithChildren<Record<string, unknown>>) => <div {...props}>{children}</div>,
  },
  useInView: () => true,
}))

import { fetchShortTermSectors } from '@/api/short-term'

const sampleItem = {
  theme_id: 1,
  theme_name: '存储芯片',
  board_kind: 'theme' as const,
  lifecycle_stage: 'fermentation' as const,
  lifecycle_confidence: 80,
  strength_score: 72,
  mainline_score: 60,
  risk_score: 20,
  limit_up_count: 3,
  failed_limit_up_count: 1,
  summary: '回流增强',
  degraded: false,
  missing_metrics: [] as string[],
}

function renderRadar(props?: {
  refreshedAtLabel?: string
  isSectionRefreshing?: boolean
  source?: string
  sourceLabel?: string
}) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ShortTermRadarSection
          refreshedAtLabel={props?.refreshedAtLabel ?? '暂无'}
          isSectionRefreshing={props?.isSectionRefreshing}
          source={props?.source}
          sourceLabel={props?.sourceLabel}
        />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ShortTermRadarSection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fetchShortTermSectors).mockResolvedValue({
      trade_date: '2026-07-24',
      items: [sampleItem],
      degraded: false,
      missing_sources: [],
    })
  })

  it('renders sector cards inside AnimatedList scroll container', async () => {
    renderRadar({ refreshedAtLabel: '10:32:15' })
    expect(await screen.findByText('存储芯片')).toBeInTheDocument()
    expect(screen.getByText('刷新于 10:32:15')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '刷新信号' })).not.toBeInTheDocument()
    expect(screen.getByTestId('radar-radar-theme-heading-scroll')).toBeInTheDocument()
    expect(screen.getByTestId('radar-sector-theme-1')).toHaveClass('item')
  })

  it('shows refreshing indicator near title', async () => {
    renderRadar({ isSectionRefreshing: true })
    expect(await screen.findByText('存储芯片')).toBeInTheDocument()
    expect(screen.getByText('刷新中…')).toBeInTheDocument()
  })

  it('shows empty state pointing to top refresh', async () => {
    vi.mocked(fetchShortTermSectors).mockResolvedValue({
      trade_date: '2026-07-24',
      items: [],
      degraded: false,
      missing_sources: [],
    })
    renderRadar()
    expect(await screen.findByText(/请使用顶部刷新/)).toBeInTheDocument()
  })

  it('requests sectors for the active theme source', async () => {
    renderRadar({ source: 'ths', sourceLabel: '同花顺' })
    await waitFor(() => {
      expect(fetchShortTermSectors).toHaveBeenCalledWith(undefined, expect.anything(), 'ths')
    })
    expect(screen.getByRole('heading', { name: /短线机会雷达 · 同花顺/ })).toBeInTheDocument()
  })

  it('shows source-specific empty copy when no snapshots', async () => {
    vi.mocked(fetchShortTermSectors).mockResolvedValue({
      trade_date: '2026-07-24',
      items: [],
      degraded: true,
      missing_sources: ['source:ths'],
    })
    renderRadar({ source: 'ths', sourceLabel: '同花顺' })
    expect(await screen.findByText(/同花顺 暂无轮动快照/)).toBeInTheDocument()
  })

  it('highlights card on hover like news list', async () => {
    const user = userEvent.setup()
    renderRadar()
    const card = await screen.findByTestId('radar-sector-theme-1')
    await user.hover(card)
    await waitFor(() => {
      expect(card).toHaveClass('selected')
    })
  })
})
