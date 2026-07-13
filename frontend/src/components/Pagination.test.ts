import { describe, it, expect } from 'vitest'
import { getVisiblePages } from './Pagination'

describe('getVisiblePages', () => {
  it('returns all pages when total <= 7', () => {
    expect(getVisiblePages(1, 5)).toEqual([1, 2, 3, 4, 5])
    expect(getVisiblePages(3, 7)).toEqual([1, 2, 3, 4, 5, 6, 7])
  })

  it('shows ellipsis after first page when current > 3', () => {
    const pages = getVisiblePages(5, 20)
    expect(pages).toContain(1)
    expect(pages).toContain('...')
    expect(pages).toContain(20)
    expect(pages).toContain(4)
    expect(pages).toContain(5)
    expect(pages).toContain(6)
  })

  it('shows ellipsis before last page when current < total - 2', () => {
    const pages = getVisiblePages(3, 20)
    expect(pages).toContain(1)
    expect(pages).toContain(20)
    expect(pages).toContain('...')
    expect(pages).toContain(2)
    expect(pages).toContain(3)
    expect(pages).toContain(4)
  })

  it('shows both ellipses when in middle', () => {
    const pages = getVisiblePages(10, 20)
    expect(pages).toEqual([1, '...', 9, 10, 11, '...', 20])
  })

  it('handles edge case at start', () => {
    const pages = getVisiblePages(1, 20)
    expect(pages[0]).toBe(1)
    expect(pages).toContain(20)
    // When current=1, shows 1,2,...,20 (ellipsis before last)
    expect(pages).toContain('...')
  })

  it('handles edge case at end', () => {
    const pages = getVisiblePages(20, 20)
    expect(pages).toContain(1)
    expect(pages[pages.length - 1]).toBe(20)
    // When current=20, shows 1,...,19,20 (ellipsis after first)
    expect(pages).toContain('...')
  })
})
