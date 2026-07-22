import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'

import { ThemeProfileSection } from './ThemeProfileSection'

it('renders structured profile and source links', () => {
  render(
    <ThemeProfileSection
      profile={{
        definition: '概念定义',
        core_logic: '核心逻辑内容',
        applications: ['制造'],
        catalysts: ['政策'],
        risks: ['竞争'],
        generated_at: '2026-07-20T00:00:00Z',
        sources: [
          { title: '来源一', url: 'https://example.com', publisher: '示例网', published_at: null },
        ],
      }}
    />
  )
  expect(screen.getByText('核心逻辑')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: '来源一' })).toHaveAttribute('rel', 'noopener noreferrer')
})

it('keeps the detailed introduction heading when profile is unavailable', () => {
  render(<ThemeProfileSection profile={null} />)

  expect(screen.getByRole('heading', { name: '题材详细介绍' })).toBeInTheDocument()
  expect(screen.getByText(/暂无详细介绍/)).toBeInTheDocument()
})
