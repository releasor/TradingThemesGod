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

function renderRadar() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ShortTermRadarSection />
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
    renderRadar()
    expect(await screen.findByText('存储芯片')).toBeInTheDocument()
    expect(screen.getByTestId('radar-radar-theme-heading-scroll')).toBeInTheDocument()
    expect(screen.getByTestId('radar-sector-theme-1')).toHaveClass('item')
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
