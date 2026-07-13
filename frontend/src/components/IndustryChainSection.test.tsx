/** IndustryChainSection 组件测试 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { IndustryChainSection } from './IndustryChainSection'
import type { IndustryChainBrief } from '@/types/theme'

const mockChains = {
  upstream: [
    {
      id: 1,
      level: 'upstream' as const,
      name: '原材料供应',
      description: '基础原材料供应商',
      representative_companies: ['公司A', '公司B'],
      sort_order: 0,
    },
  ],
  midstream: [
    {
      id: 2,
      level: 'midstream' as const,
      name: '生产制造',
      description: '产品制造和加工',
      representative_companies: ['公司C'],
      sort_order: 0,
    },
  ],
  downstream: [
    {
      id: 3,
      level: 'downstream' as const,
      name: '销售渠道',
      description: '产品销售和分销',
      representative_companies: null,
      sort_order: 0,
    },
  ],
}

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })
}

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = createQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  )
}

describe('IndustryChainSection', () => {
  it('renders three columns', () => {
    renderWithQuery(
      <IndustryChainSection chains={mockChains} themeId={1} />
    )

    expect(screen.getByText('上游')).toBeInTheDocument()
    expect(screen.getByText('中游')).toBeInTheDocument()
    expect(screen.getByText('下游')).toBeInTheDocument()
  })

  it('renders chain point names', () => {
    renderWithQuery(
      <IndustryChainSection chains={mockChains} themeId={1} />
    )

    expect(screen.getByText('原材料供应')).toBeInTheDocument()
    expect(screen.getByText('生产制造')).toBeInTheDocument()
    expect(screen.getByText('销售渠道')).toBeInTheDocument()
  })

  it('renders chain point descriptions', () => {
    renderWithQuery(
      <IndustryChainSection chains={mockChains} themeId={1} />
    )

    expect(screen.getByText('基础原材料供应商')).toBeInTheDocument()
    expect(screen.getByText('产品制造和加工')).toBeInTheDocument()
    expect(screen.getByText('产品销售和分销')).toBeInTheDocument()
  })

  it('renders representative companies', () => {
    renderWithQuery(
      <IndustryChainSection chains={mockChains} themeId={1} />
    )

    expect(screen.getByText('公司A')).toBeInTheDocument()
    expect(screen.getByText('公司B')).toBeInTheDocument()
    expect(screen.getByText('公司C')).toBeInTheDocument()
  })

  it('shows empty state when no chain points', () => {
    const emptyChains = {
      upstream: [],
      midstream: [],
      downstream: [],
    }

    renderWithQuery(
      <IndustryChainSection chains={emptyChains} themeId={1} />
    )

    const emptyStates = screen.getAllByText('暂无数据')
    expect(emptyStates).toHaveLength(3)
  })

  it('handles missing chain level gracefully', () => {
    const partialChains = {
      upstream: mockChains.upstream,
      midstream: [],
      downstream: [],
    }

    renderWithQuery(
      <IndustryChainSection chains={partialChains} themeId={1} />
    )

    expect(screen.getByText('原材料供应')).toBeInTheDocument()
    expect(screen.getByText('中游')).toBeInTheDocument()
    expect(screen.getByText('下游')).toBeInTheDocument()
  })
})
