import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'

import { ThemeDriverEvents } from './ThemeDriverEvents'

it('renders at most five driver events', () => {
  const events = Array.from({ length: 6 }, (_, index) => ({
    id: index,
    title: `事件${index}`,
    summary: '摘要',
    source: '来源',
    url: `https://example.com/${index}`,
    published_at: '2026-07-20T00:00:00Z',
    crawled_at: '2026-07-20T00:00:00Z',
    relevance_score: 80,
  }))
  render(<ThemeDriverEvents events={events} />)
  expect(screen.getAllByTestId('driver-event')).toHaveLength(5)
})
