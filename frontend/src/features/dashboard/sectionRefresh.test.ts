import { describe, expect, it, beforeEach } from 'vitest'
import {
  SECTION_IDS,
  readSectionRefreshedAt,
  writeSectionRefreshedAt,
  formatSectionRefreshedAt,
} from './sectionRefresh'

describe('sectionRefresh', () => {
  beforeEach(() => localStorage.clear())

  it('persists and formats section timestamps', () => {
    const at = '2026-07-27T02:32:15.000Z'
    writeSectionRefreshedAt(SECTION_IDS.heatRanking, at)
    expect(readSectionRefreshedAt(SECTION_IDS.heatRanking)).toBe(at)
    expect(formatSectionRefreshedAt(at)).toMatch(/\d{2}:\d{2}:\d{2}/)
  })

  it('returns null when missing', () => {
    expect(readSectionRefreshedAt(SECTION_IDS.riseRanking)).toBeNull()
    expect(formatSectionRefreshedAt(null)).toBe('暂无')
  })
})
