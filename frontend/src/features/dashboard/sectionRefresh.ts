export const SECTION_IDS = {
  heatRanking: 'heat-ranking',
  riseRanking: 'rise-ranking',
  strategyCard: 'strategy-card',
  shortTermRadar: 'short-term-radar',
  firstToSecond: 'first-to-second',
  marketSignals: 'market-signals',
  indicatorSignals: 'indicator-signals',
} as const

export type SectionId = (typeof SECTION_IDS)[keyof typeof SECTION_IDS]

const STORAGE_PREFIX = 'dashboard-section-refreshed-at:'

export function readSectionRefreshedAt(id: SectionId): string | null {
  try {
    return localStorage.getItem(STORAGE_PREFIX + id)
  } catch {
    return null
  }
}

export function writeSectionRefreshedAt(id: SectionId, iso: string): void {
  try {
    localStorage.setItem(STORAGE_PREFIX + id, iso)
  } catch {
    /* ignore quota */
  }
}

export function formatSectionRefreshedAt(iso: string | null): string {
  if (!iso) return '暂无'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '暂无'
  return d.toLocaleTimeString('zh-CN', { hour12: false })
}

const FIRST_TO_SECOND_CACHE_KEY = 'dashboard-last-first-to-second'

export function readLastFirstToSecondCache<T = unknown>(): T | undefined {
  try {
    const raw = sessionStorage.getItem(FIRST_TO_SECOND_CACHE_KEY)
    if (!raw) return undefined
    return JSON.parse(raw) as T
  } catch {
    return undefined
  }
}

export function writeLastFirstToSecondCache(data: unknown): void {
  try {
    sessionStorage.setItem(FIRST_TO_SECOND_CACHE_KEY, JSON.stringify(data))
  } catch {
    /* ignore quota */
  }
}
