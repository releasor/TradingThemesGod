/** 看板活跃题材数据源（localStorage 偏好） */

const STORAGE_KEY = 'ttg.active_dashboard_source'
export const DEFAULT_DASHBOARD_SOURCE = 'eastmoney'

export function readActiveDashboardSource(): string {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)?.trim()
    return raw || DEFAULT_DASHBOARD_SOURCE
  } catch {
    return DEFAULT_DASHBOARD_SOURCE
  }
}

export function writeActiveDashboardSource(source: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, source)
  } catch {
    // ignore quota / private mode
  }
}
